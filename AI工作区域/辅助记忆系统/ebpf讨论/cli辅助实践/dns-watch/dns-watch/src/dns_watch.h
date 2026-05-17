#ifndef DNS_WATCH_H
#define DNS_WATCH_H

#ifndef __VMLINUX_H__
#include <linux/types.h>
#endif

#define DNS_WATCH_COMM_LEN 16
#define DNS_WATCH_QUERY_LEN 256

struct dns_watch_inflight {
	__u64 start_ns;
	char comm[DNS_WATCH_COMM_LEN];
	char query_name[DNS_WATCH_QUERY_LEN];
};

struct dns_watch_event {
	__u64 ts_ns;
	__u64 resolver_call_latency_ns;
	__u32 pid;
	__u32 tid;
	char comm[DNS_WATCH_COMM_LEN];
	char query_name[DNS_WATCH_QUERY_LEN];
};

#endif
