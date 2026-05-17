# dns-watch

A small exploratory eBPF/network observability project.

## Current goal

Trace DNS activity triggered by a specified process and turn it into a small, readable diagnostic view.

For version 0, the focus is intentionally narrow:
- observe DNS activity from a target process
- produce readable output
- support one believable troubleshooting-style explanation

This project is **not** yet trying to solve the full DNS-to-connect lifecycle.

---

## Why this exists

In real troubleshooting, DNS is often the beginning of a larger chain:

1. a process wants to reach a service
2. it performs a DNS lookup
3. the lookup succeeds or fails
4. one or more IP addresses may be returned
5. the process attempts a follow-up connection
6. the connection may succeed, fail, or retry another address

When that chain is not visible, engineers guess.

`dns-watch` starts by making the DNS part of that chain more observable from a process-centric point of view.

---

## Version 0 focus

Version 0 is mainly trying to answer:

> Can we observe DNS query activity from a specified process in a way that is simple, readable, and useful enough to explain one concrete example?

Desired v0 output fields:
- timestamp
- pid
- tid
- comm
- query name
- resolver_call_latency_ms

Example v0 event line:
`2026-05-17T18:00:00.000Z pid=1234 tid=1234 comm=curl query_name=example.com resolver_call_latency_ms=12.4`

---

## Not in version 0

The following are intentionally out of scope unless explicitly pulled in later:
- downstream `connect()` correlation
- returned IP analysis
- retry / alternate-IP analysis
- dashboards
- persistent storage
- polished production UX
- full protocol coverage

---

## Source of truth

Current project framing lives in:

- `docs/briefs/dns-watch-brief.md`

Behavior-level specification lives in:

- `specs/dns-watch/spec.md`

Current project tasks and sequencing live in:

- `dns-watch/TODO.md`

Open questions live in:

- `dns-watch/questions.md`

Scope decisions live in:

- `dns-watch/decision-log.md`

---

## Current working mode

This project is being developed as:
- a narrow MVP exploration
- a learning bridge from libbpf/eBPF into network observability
- a teammate-readable diagnostic experiment
- a controlled environment for using Copilot CLI to clarify requirements and iterate

The main rule is:
- keep v0 small
- keep uncertainty visible
- prefer believable progress over impressive scope

---

## Suggested workflow

1. Read the current brief
2. Narrow the v0 scope
3. Refine the implementation direction
4. Review the idea critically
5. Create a short task plan
6. Build the smallest believable demo
7. Decide whether v1 is justified

---

## Prompts

See:

- `dns-watch/prompts/session.md`
- `dns-watch/prompts/kickoff.md`
- `dns-watch/prompts/refine.md`
- `dns-watch/prompts/review.md`
- `dns-watch/prompts/plan.md`
- `dns-watch/prompts/write-todo.md`
- `dns-watch/prompts/demo.md`

---

## Status

v0 now has a minimal implementation skeleton:
- `src/dns_watch.bpf.c` traces `getaddrinfo()` entry and return
- `src/dns_watch.c` loads the BPF program, filters by PID, and prints one event line per completed resolver call
- `scripts/demo.sh` and `scripts/verify.sh` provide one narrow `curl http://example.com` demo flow

The current emphasis is still:
- scope control
- believable demo-oriented progress
- proving attach/runtime behavior under the actual WSL2 privilege constraints

---

## Current implementation slice

Current v0 implementation direction now exists in code:
- attach uprobe + uretprobe to libc `getaddrinfo()`
- filter in BPF by one specified PID
- pair entry and return on the same thread
- emit a readable line with
  `timestamp pid tid comm query_name resolver_call_latency_ms`

Example output shape:
`2026-05-17T18:00:00.000Z pid=1234 tid=1234 comm=curl query_name=example.com resolver_call_latency_ms=12.4`

---

## Build

```bash
cd dns-watch
make
```

This produces:
- `dns-watch` - userspace loader / printer
- `.output/dns_watch.bpf.o` - BPF object
- `.output/dns_watch.skel.h` - generated skeleton

---

## Run

Direct PID mode:

```bash
sudo ./dns-watch -p <pid>
```

First narrow demo:

```bash
sudo ./scripts/demo.sh
```

First narrow verification:

```bash
sudo ./scripts/verify.sh
```

Notes:
- the default libc attachment path is `/lib/x86_64-linux-gnu/libc.so.6`
- the current WSL2 setup likely requires elevated privileges for memlock/BPF load/uprobe attach
- the demo script uses `sh -c 'sleep 2; exec curl ...'` so the traced PID stays stable while still exercising `curl`
