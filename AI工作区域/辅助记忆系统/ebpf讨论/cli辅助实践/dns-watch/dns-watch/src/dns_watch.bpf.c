#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>
#include "dns_watch.h"

const volatile __u32 target_pid = 0;

struct {
	__uint(type, BPF_MAP_TYPE_HASH);
	__uint(max_entries, 10240);
	__type(key, __u64);
	__type(value, struct dns_watch_inflight);
} inflight SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_RINGBUF);
	__uint(max_entries, 1 << 24);
} events SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 4);
	__type(key, __u32);
	__type(value, __u64);
} stats SEC(".maps");

static __always_inline void copy_literal(char *dst, const char *src, __u32 len)
{
	__builtin_memcpy(dst, src, len);
}

static __always_inline void bump_stat(__u32 index)
{
	__u64 init_value = 1;
	__u64 *value;

	value = bpf_map_lookup_elem(&stats, &index);
	if (value)
		__sync_fetch_and_add(value, 1);
	else
		bpf_map_update_elem(&stats, &index, &init_value, BPF_ANY);
}

static __always_inline void capture_query_name(struct dns_watch_inflight *lookup,
						       const char *node)
{
	long copied;

	if (!node) {
		copy_literal(lookup->query_name, "<null>", sizeof("<null>"));
		return;
	}

	copied = bpf_probe_read_user_str(lookup->query_name, sizeof(lookup->query_name), node);
	if (copied < 0)
		copy_literal(lookup->query_name, "<unreadable>", sizeof("<unreadable>"));
}

SEC("uprobe")
int BPF_KPROBE(handle_getaddrinfo_enter, const char *node, const char *service,
	       const void *hints, void *res)
{
	__u64 pid_tgid = bpf_get_current_pid_tgid();
	__u32 tgid = pid_tgid >> 32;
	struct dns_watch_inflight lookup = {};

	(void)service;
	(void)hints;
	(void)res;

	bump_stat(0);
	if (target_pid && tgid != target_pid)
		return 0;

	bump_stat(1);
	lookup.start_ns = bpf_ktime_get_ns();
	bpf_get_current_comm(&lookup.comm, sizeof(lookup.comm));
	capture_query_name(&lookup, node);
	bpf_map_update_elem(&inflight, &pid_tgid, &lookup, BPF_ANY);
	return 0;
}

SEC("uretprobe")
int BPF_KRETPROBE(handle_getaddrinfo_exit, int ret)
{
	__u64 pid_tgid = bpf_get_current_pid_tgid();
	__u32 tgid = pid_tgid >> 32;
	struct dns_watch_inflight *lookup;
	struct dns_watch_event *event;

	(void)ret;

	bump_stat(2);
	if (target_pid && tgid != target_pid)
		return 0;

	bump_stat(3);
	lookup = bpf_map_lookup_elem(&inflight, &pid_tgid);
	if (!lookup)
		return 0;

	event = bpf_ringbuf_reserve(&events, sizeof(*event), 0);
	if (!event) {
		bpf_map_delete_elem(&inflight, &pid_tgid);
		return 0;
	}

	event->ts_ns = bpf_ktime_get_ns();
	event->resolver_call_latency_ns = event->ts_ns - lookup->start_ns;
	event->pid = tgid;
	event->tid = pid_tgid;
	__builtin_memcpy(event->comm, lookup->comm, sizeof(event->comm));
	__builtin_memcpy(event->query_name, lookup->query_name, sizeof(event->query_name));

	bpf_ringbuf_submit(event, 0);
	bpf_map_delete_elem(&inflight, &pid_tgid);
	return 0;
}

char LICENSE[] SEC("license") = "Dual BSD/GPL";
