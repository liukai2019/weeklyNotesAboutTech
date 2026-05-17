#include <errno.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/resource.h>

#include <linux/types.h>
#include "bpf.h"
#include "libbpf.h"

#include "dns_watch.h"
#include "dns_watch.skel.h"

static struct env {
	pid_t pid;
	bool verbose;
	const char *libc_path;
} env = {
	.libc_path = "/lib/x86_64-linux-gnu/libc.so.6",
};

static volatile sig_atomic_t exiting;
static long long boot_to_real_ns;

static void sig_handler(int sig)
{
	(void)sig;
	exiting = 1;
}

static void usage(const char *prog)
{
	fprintf(stderr,
		"Usage: %s -p PID [-l LIBC_PATH] [-v]\n"
		"\n"
		"Trace getaddrinfo() resolver calls for one target PID and print\n"
		"timestamp pid tid comm query_name resolver_call_latency_ms.\n"
		"\n"
		"Options:\n"
		"  -p PID        target PID to observe\n"
		"  -l LIBC_PATH  libc path for getaddrinfo() uprobe attachment\n"
		"  -v            enable libbpf debug logging\n",
		prog);
}

static int parse_args(int argc, char **argv)
{
	int opt;

	while ((opt = getopt(argc, argv, "p:l:v")) != -1) {
		switch (opt) {
		case 'p':
			env.pid = (pid_t)strtol(optarg, NULL, 10);
			break;
		case 'l':
			env.libc_path = optarg;
			break;
		case 'v':
			env.verbose = true;
			break;
		default:
			usage(argv[0]);
			return -EINVAL;
		}
	}

	if (env.pid <= 0) {
		usage(argv[0]);
		return -EINVAL;
	}

	return 0;
}

static int libbpf_print_fn(enum libbpf_print_level level, const char *format, va_list args)
{
	if (level == LIBBPF_DEBUG && !env.verbose)
		return 0;

	return vfprintf(stderr, format, args);
}

static int bump_memlock_rlimit(void)
{
	struct rlimit rlim = {
		.rlim_cur = RLIM_INFINITY,
		.rlim_max = RLIM_INFINITY,
	};

	return setrlimit(RLIMIT_MEMLOCK, &rlim);
}

static long long timespec_to_ns(const struct timespec *ts)
{
	return (long long)ts->tv_sec * 1000000000LL + ts->tv_nsec;
}

static int init_clock_offset(void)
{
	struct timespec real_ts;
	struct timespec boot_ts;

	if (clock_gettime(CLOCK_REALTIME, &real_ts) != 0)
		return -errno;
	if (clock_gettime(CLOCK_BOOTTIME, &boot_ts) != 0)
		return -errno;

	boot_to_real_ns = timespec_to_ns(&real_ts) - timespec_to_ns(&boot_ts);
	return 0;
}

static void format_iso8601_utc(__u64 monotonic_ns, char *buf, size_t buf_len)
{
	unsigned long long real_ns = monotonic_ns + boot_to_real_ns;
	time_t seconds = real_ns / 1000000000ULL;
	unsigned int millis = (real_ns % 1000000000ULL) / 1000000ULL;
	char base[32];
	struct tm tm = {};

	gmtime_r(&seconds, &tm);
	strftime(base, sizeof(base), "%Y-%m-%dT%H:%M:%S", &tm);
	snprintf(buf, buf_len, "%s.%03uZ", base, millis);
}

static int handle_event(void *ctx, void *data, size_t data_sz)
{
	const struct dns_watch_event *event = data;
	char timestamp[40];

	(void)ctx;
	(void)data_sz;

	format_iso8601_utc(event->ts_ns, timestamp, sizeof(timestamp));
	printf("%s pid=%u tid=%u comm=%s query_name=%s resolver_call_latency_ms=%.3f\n",
	       timestamp, event->pid, event->tid, event->comm, event->query_name,
	       (double)event->resolver_call_latency_ns / 1000000.0);
	fflush(stdout);
	return 0;
}

static int attach_programs(struct dns_watch_bpf *skel)
{
	LIBBPF_OPTS(bpf_uprobe_opts, entry_opts,
		.func_name = "getaddrinfo",
		.retprobe = false);
	LIBBPF_OPTS(bpf_uprobe_opts, exit_opts,
		.func_name = "getaddrinfo",
		.retprobe = true);
	int err;

	skel->links.handle_getaddrinfo_enter =
		bpf_program__attach_uprobe_opts(skel->progs.handle_getaddrinfo_enter,
						env.pid, env.libc_path, 0, &entry_opts);
	err = libbpf_get_error(skel->links.handle_getaddrinfo_enter);
	if (err)
		return err;

	skel->links.handle_getaddrinfo_exit =
		bpf_program__attach_uprobe_opts(skel->progs.handle_getaddrinfo_exit,
						env.pid, env.libc_path, 0, &exit_opts);
	err = libbpf_get_error(skel->links.handle_getaddrinfo_exit);
	if (err)
		return err;

	return 0;
}

int main(int argc, char **argv)
{
	struct dns_watch_bpf *skel = NULL;
	struct ring_buffer *rb = NULL;
	int err;

	err = parse_args(argc, argv);
	if (err)
		return 1;

	libbpf_set_print(libbpf_print_fn);

	if (bump_memlock_rlimit() != 0) {
		fprintf(stderr, "Failed to raise RLIMIT_MEMLOCK: %s\n", strerror(errno));
		return 1;
	}

	err = init_clock_offset();
	if (err) {
		fprintf(stderr, "Failed to initialize clock offset: %s\n", strerror(-err));
		return 1;
	}

	signal(SIGINT, sig_handler);
	signal(SIGTERM, sig_handler);

	skel = dns_watch_bpf__open();
	if (!skel) {
		fprintf(stderr, "Failed to open BPF skeleton\n");
		return 1;
	}

	skel->rodata->target_pid = env.pid;

	err = dns_watch_bpf__load(skel);
	if (err) {
		fprintf(stderr, "Failed to load and verify BPF skeleton: %d\n", err);
		goto cleanup;
	}

	err = attach_programs(skel);
	if (err) {
		fprintf(stderr, "Failed to attach getaddrinfo uprobes on %s: %d\n",
			env.libc_path, err);
		goto cleanup;
	}

	rb = ring_buffer__new(bpf_map__fd(skel->maps.events), handle_event, NULL, NULL);
	if (!rb) {
		err = -errno;
		fprintf(stderr, "Failed to create ring buffer: %s\n", strerror(errno));
		goto cleanup;
	}

	while (!exiting) {
		err = ring_buffer__poll(rb, 100);
		if (err == -EINTR) {
			err = 0;
			break;
		}
		if (err < 0) {
			fprintf(stderr, "ring_buffer__poll failed: %d\n", err);
			break;
		}
	}

cleanup:
	ring_buffer__free(rb);
	dns_watch_bpf__destroy(skel);
	return err < 0 ? -err : err;
}
