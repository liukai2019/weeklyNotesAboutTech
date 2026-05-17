# Decision log

## 2026-05-17

### Decision: use a brief as the current source of truth
For now, `docs/briefs/dns-watch-brief.md` is the main source of truth for framing, scope, constraints, and open questions.

Reason:
- the behavior spec is still evolving
- the project is still in MVP discovery mode
- forcing premature precision would create false clarity

---

### Decision: keep `specs/dns-watch/spec.md` as a real file, but allow it to evolve slowly
The spec file exists and may be partially filled, but it should not be treated as fully authoritative before the behavior is better understood.

Reason:
- behavior-level expectations are not stable yet
- Given/When/Then coverage should follow understanding, not fake it

---

### Decision: dns-watch is the first concrete observability problem
The first project in this workspace is `dns-watch`.

Reason:
- it is narrow enough to be a plausible MVP
- it is relevant to real teammate concerns
- it is a good bridge from libbpf/eBPF learning into network observability

---

### Decision: v0 focuses on DNS observation only
Version 0 is about observing DNS activity from a specified process, not full DNS-to-connect lifecycle correlation.

Reason:
- this keeps the first version small and believable
- it reduces the chance of scope explosion
- it allows earlier validation

---

### Decision: keep output teammate-readable
Readable human output is a first-class goal for v0.

Reason:
- the project is not just a technical exercise
- usefulness includes the ability to explain one concrete example to another engineer

---

### Decision: defer richer correlation features
The following are deferred beyond v0 unless strong evidence appears:
- downstream `connect()` correlation
- returned IP analysis
- retry/alternate-IP behavior
- broader timeline correlation

Reason:
- these are valuable but would overload the first version
- the first question is whether process-level DNS observation is useful enough on its own

---

### Decision: v0 is PID-only and excludes child processes
Version 0 targets one specified PID only.
Child-process tracking is explicitly out of scope for v0.

Reason:
- it keeps filtering behavior unambiguous
- it reduces early matching and attribution complexity
- it is enough to support one believable demo

---

### Decision: v0 proves query name plus resolver-call latency, not returned IPs
Version 0 should prove that a specified process performed a DNS lookup for a query name and that the enclosing resolver call took approximately N milliseconds.
Returned-IP output is deferred beyond v0.

Reason:
- query name is necessary to make the output explainable to a teammate
- resolver-call latency is necessary to make the event diagnostically useful
- returned-IP parsing adds meaningful response-path complexity that is not required for the first believable slice

---

### Decision: name the v0 latency field `resolver_call_latency_ms`
Version 0 should not use the generic field name `latency`.
The event field should be named `resolver_call_latency_ms`.

Reason:
- it makes the measurement semantics explicit
- it avoids confusion with future DNS packet-level timing
- it leaves room for later fields such as `dns_packet_latency_ms`

---

### Decision: `resolver_call_latency_ms` means `getaddrinfo()` call duration
For v0, `resolver_call_latency_ms` means the elapsed time from entry to return of one `getaddrinfo()` call on the same thread.
It should be described as resolver-call duration, not packet latency.

Good-enough standard for v0:
- entry and return can be paired reliably for one call on one thread
- the reported unit is milliseconds
- the documentation states clearly that this is `getaddrinfo()` call duration

Reason:
- this gives v0 a precise and honest timing meaning
- it is measurable with the chosen uprobe/uretprobe path
- it avoids overclaiming wire-level DNS timing

---

### Decision: v0 observation path is `getaddrinfo()` uprobe/uretprobe
Version 0 should observe one specified PID by attaching to `getaddrinfo()` entry and return.
The first implementation path is userspace-function observation, not DNS packet parsing.

Matching strategy for v0:
- pair one `getaddrinfo()` entry with one `getaddrinfo()` return on the same thread
- compute `resolver_call_latency_ms` from entry timestamp to return timestamp

Kernel/userspace split for v0:
- eBPF captures function-boundary events and timing data
- userspace formats and prints the resulting event stream

First demo scenario for v0:
- run one repeatable command that triggers name resolution for a known host
- the initial default should be a single `curl http://example.com` process

Reason:
- this is the smallest believable path that can produce query name plus resolver-call latency
- it avoids packet-level parsing and request/response matching complexity
- it keeps the first demo narrow and explainable

---

### Decision: v0 event schema includes `tid`
The v0 event schema should be:
`timestamp pid tid comm query_name resolver_call_latency_ms`

Field notes:
- `timestamp`: event time for the emitted lookup record
- `pid`: target process identifier
- `tid`: thread identifier used for entry/return pairing semantics
- `comm`: process or thread command name
- `query_name`: requested name passed into resolution
- `resolver_call_latency_ms`: elapsed time from `getaddrinfo()` entry to return

Reason:
- `tid` makes the same-thread pairing model explicit
- the schema stays minimal while still matching the chosen implementation path
- it gives one readable event shape for the first demo and docs

---

### Decision: the first passing demo proves one narrow resolver story
The first passing demo should prove only this:
- for one specified `curl http://example.com` process
- `dns-watch` can emit at least one event with
  `timestamp pid tid comm query_name resolver_call_latency_ms`
- the `query_name` is the requested host name
- `resolver_call_latency_ms` is non-empty and explained as `getaddrinfo()` call duration

The first passing demo should not claim:
- DNS packet-level timing
- returned IP visibility
- DNS success or failure semantics
- downstream `connect()` correlation
- coverage of every resolver path

Reason:
- this keeps the first demo small enough to be believable
- it aligns the demo claim with the chosen measurement semantics
- it gives a crisp pass/fail target before any implementation work

---

### Decision: the first sample output should be one plain-text event line
The first sample output should be a single plain-text line with stable field order:

`2026-05-17T18:00:00.000Z pid=1234 tid=1234 comm=curl query_name=example.com resolver_call_latency_ms=12.4`

Sample-output goals:
- immediately readable by a teammate in a terminal
- matches the v0 event schema exactly
- shows one believable `curl http://example.com` lookup story

Formatting notes:
- `timestamp` should be an ISO-8601 wall-clock string
- the remaining fields should use `key=value` formatting
- one line should represent one completed `getaddrinfo()` call

Reason:
- a concrete sample line makes the intended UX and schema harder to misunderstand
- plain text is enough for v0 and keeps output review simple
- this gives implementation work a precise target without expanding scope

---

### Decision: uncertainty must remain visible
Open questions should remain visible in documents instead of being silently guessed away.

Reason:
- false clarity is a major risk in this project
- maintaining visibility of uncertainty improves control over scope and design

---

### Decision: implement v0 around a global libc uprobe plus BPF PID filter
The first implementation should attach `getaddrinfo()` uprobes to libc and then filter to one target PID inside BPF.

Reason:
- this keeps the event semantics aligned with the PID-only v0 scope
- it avoids needing a symbol offset lookup path in the first slice
- it makes short-lived demo targets more practical than per-process attach alone

---

### Decision: use a same-PID exec demo for the first curl story
The first demo script should start a shell that sleeps briefly and then `exec`s `curl http://example.com`, so the traced PID remains stable while still exercising curl itself.

Reason:
- it preserves the v0 rule that filtering is by one PID
- it avoids child-process tracking
- it gives the watcher time to attach before the DNS lookup happens

---

### Decision: treat root as necessary but not sufficient
Root-mode execution is necessary for the current WSL2 setup, but it does not by itself make the current libc `getaddrinfo()` observation path viable.

Reason:
- root-mode validation removed the memlock/load blocker
- `dns-watch` could create libc uprobe links successfully
- despite that, controlled tests still produced zero probe hits

---

### Decision: stop treating libc `getaddrinfo()` as the only plausible v0 hook
The current libc `getaddrinfo()` path remains the baseline design, but it should now be treated as a suspect observation point rather than an assumed-good one.

Reason:
- the design was plausible on paper
- runtime evidence does not yet support it on this machine
- continuing to debug only around `getaddrinfo()` is less valuable than comparing alternative resolver symbols

---

### Decision: prefer `libresolv.so.2` symbols for the next spike
The next narrow investigation should start with `libresolv.so.2` symbols such as `__res_context_search`, `__res_nsearch`, and `__res_nquery`.

Reason:
- they are closer to actual resolver work than the top-level libc wrapper
- they are more likely to indicate real DNS activity if the libc wrapper path is bypassed or behaves unexpectedly
- this keeps the next step small while still staying within the DNS-observation problem
