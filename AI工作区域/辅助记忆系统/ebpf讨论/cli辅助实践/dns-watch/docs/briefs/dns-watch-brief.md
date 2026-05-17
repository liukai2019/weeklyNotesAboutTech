# dns-watch brief

## Status

Active working brief.

This document is the current source of truth for problem framing, MVP scope, constraints, and open questions.

It is **not** the final behavior specification.
Behavior-level requirements and Given/When/Then scenarios belong in `specs/dns-watch/spec.md`.

---

## 1. Working title

dns-watch

Trace DNS activity triggered by a specified process and turn it into a small, readable diagnostic view.

---

## 2. Core problem

When a target process performs DNS lookups, engineers often cannot quickly answer simple but important questions:

- Did the process perform a DNS lookup at all?
- What name did it try to resolve?
- How long did the lookup take?
- Did the lookup appear to succeed or fail?
- If it succeeded, what happened next?

In real troubleshooting, DNS behavior is often discussed together with later connection behavior, but the causal chain is usually not clearly visible in one place.

This project starts with the DNS part of that chain.

---

## 3. Why this matters

This problem is relevant beyond toy learning.

In practical engineering environments, DNS resolution is often the beginning of a larger sequence:

1. a process needs to reach a service
2. it performs a DNS lookup
3. the lookup succeeds or fails
4. if it succeeds, one or more IP addresses are returned
5. the process attempts a follow-up connection
6. the connection succeeds, fails, or retries another address

If that chain is unclear, engineers end up guessing.

The immediate value of `dns-watch` is to make the DNS portion observable in a process-centric way.

The broader value is to support a more explainable and story-friendly diagnostic workflow for network-related behavior.

---

## 4. Intended user

Primary users:
- engineers investigating network behavior of a known process
- engineers who suspect DNS behavior contributes to downstream failures
- engineers learning eBPF and network observability by building a narrow but realistic tool

Secondary users:
- future work on process/network/agent behavior correlation

---

## 5. Why this project exists now

There are two reasons to do this now.

### 5.1 Technical reason
This is a narrow observability problem that may be small enough to build as an MVP, while still being realistic and extensible.

It is a good bridge between:
- learning eBPF/libbpf
- understanding network observability
- eventually exploring richer correlation such as DNS-to-connect or agent/network/file timelines

### 5.2 Work/story reason
This topic is close to real teammate concerns.

In work-like scenarios, engineers care about things such as:
- whether DNS lookup itself failed
- whether different returned IPs lead to different connection outcomes
- whether retries or alternate IP selection happened
- whether an engineer can explain the sequence clearly to others

That makes `dns-watch` useful not only as a learning project, but also as a seed for a diagnostic story that other engineers can recognize.

---

## 6. Why eBPF may be the right tool

eBPF is potentially a good fit because it may allow process-scoped, low-intrusion observation of DNS-related activity without requiring direct changes to the target application.

Possible advantages:
- process-aware visibility
- low-intrusion observation
- extensibility toward broader network observability
- future correlation with process/file/network/system behavior

However, eBPF must be justified by actual value.

This project should not assume that eBPF is automatically the best answer.
One explicit goal of the early phase is to learn whether eBPF gives enough unique leverage for this problem compared with simpler tools.

---

## 7. Current project focus

Current focus is **not** the full DNS-to-connect lifecycle.

Current focus is:

> Observe DNS queries triggered by a specified process and produce a small, readable event stream containing basic timing and identity information.

This should be treated as a scoped MVP discovery effort, not a full network diagnosis platform.

---

## 8. MVP goal for version 0

Version 0 should answer this question:

> For a specified target process, can we observe DNS query activity in a way that is simple, readable, and useful enough to explain one concrete example to another engineer?

### v0 desired outputs
For each observed DNS lookup, try to produce:
- timestamp
- pid
- tid
- comm
- query name
- resolver_call_latency_ms

Current v0 event schema:
`timestamp pid tid comm query_name resolver_call_latency_ms`

### v0 scope decisions now fixed
- filtering is by a specified pid
- child processes are out of scope
- query name is required for usefulness
- resolver call latency is required for usefulness
- returned IP output is deferred beyond v0

### v0 success condition
Version 0 is useful if:
- it can target a known process
- it can show at least some DNS activity from that process
- it can present output that is readable by a human
- it can support one concrete troubleshooting-style explanation

Example of such an explanation:
- process X tried to resolve name Y
- the lookup took Z milliseconds
- this provides evidence that DNS activity occurred before later network steps

First passing demo target:
- one specified `curl http://example.com` process produces at least one readable event
- the event contains `timestamp pid tid comm query_name resolver_call_latency_ms`
- the demo claim is limited to resolver-call observation, not packet-level DNS behavior

First sample output target:
`2026-05-17T18:00:00.000Z pid=1234 tid=1234 comm=curl query_name=example.com resolver_call_latency_ms=12.4`

---

## 9. What v0 is trying to prove

Version 0 is mainly a proof of usefulness, not a proof of completeness.

It should help answer:
- Is process-level DNS observation useful enough to keep building?
- Which fields are actually necessary?
- Is query name extraction practical in the chosen approach?
- Is resolver-call latency estimation practical and trustworthy enough for a first tool?
- Is the output understandable by someone other than the author?

For v0, `resolver_call_latency_ms` means the elapsed time of one `getaddrinfo()` call from function entry to function return on the same thread.
It is resolver-call duration, not DNS packet request/response latency.

---

## 10. Non-goals for version 0

Version 0 should **not** try to do all of the following at once.

Out of scope for v0:
- full DNS protocol coverage
- complete support for every resolver path
- full correlation with downstream `connect()` success/failure
- full process tree tracking
- returned IP output
- retry/alternate-IP analysis
- dashboards or persistent storage
- polished production UX
- upstream-ready packaging
- complete root-cause diagnosis of all network failures

If any of these become necessary, they should be treated as later phases, not silently pulled into v0.

---

## 11. Candidate expansions after v0

Potential v1+ directions:
- indicate DNS success/failure more explicitly
- capture response code
- capture returned IP addresses
- correlate DNS result with later `connect()` attempts
- detect retry or alternate-IP behavior
- support process tree tracking
- output JSON
- add summary views or aggregates
- support timeline-style correlation with broader network events

These are intentionally deferred until v0 proves useful.

---

## 12. Assumptions

Current working assumptions:
- a narrow, process-scoped DNS view is easier to validate than full network correlation
- a simple event stream is more important than a polished UI
- query name and latency are higher-priority than advanced protocol completeness
- the first value comes from visibility, not completeness
- some ambiguity is acceptable in the brief phase, as long as it is visible and documented

---

## 13. Constraints and realities

This project is being developed under practical constraints:
- limited time
- self-directed learning
- evolving understanding of eBPF/libbpf
- need for low-friction iteration
- desire for outputs that are technically useful and also explainable to others

This means the project should optimize for:
- small steps
- visible progress
- clear tradeoffs
- concrete demos
- low ceremony

---

## 14. Key open questions

These are still unresolved and should stay visible.

### Product questions
- What is the narrowest useful definition of “DNS watch” for v0?
- Is query name enough for first usefulness, or are result details required?
- Should v0 show only event-level data, or also light summaries?
- Who is the main consumer of the output: the author, a teammate, or a future upstream audience?

### Scope questions
- Should filtering be by pid, comm, or both?
- Should child processes be included?
- Should v0 handle only basic DNS request/response observation?
- Are returned IP addresses required for the first truly useful version?

### Technical questions
- What are the main environment constraints in WSL2 for the chosen `getaddrinfo()` uprobe/uretprobe path?
- How much parsing should happen before output is emitted?

Current v0 implementation direction:
- observe one specified pid via `getaddrinfo()` entry and return
- pair entry and return on the same thread
- compute `resolver_call_latency_ms` from function entry to function return
- keep eBPF responsible for lightweight capture and timing
- keep userspace responsible for readable output
- start with one repeatable demo command: `curl http://example.com`
- What are the important WSL2/kernel/environment limitations for the first implementation?

---

## 15. Risks

### Risk 1: false clarity
There is a risk of pretending the problem is more clearly defined than it really is.

Mitigation:
- keep open questions visible
- avoid overcommitting the spec too early

### Risk 2: overloading v0
There is a risk of dragging in connect correlation, returned IP analysis, retries, and broader diagnostics too early.

Mitigation:
- enforce non-goals
- keep v0 focused on DNS observation only

### Risk 3: building technically interesting but practically weak output
There is a risk of collecting data that looks impressive but does not help a human explain what happened.

Mitigation:
- optimize for readability and one concrete explanation
- prioritize fields that support real interpretation

### Risk 4: eBPF-first thinking without enough justification
There is a risk of choosing eBPF because it is interesting rather than because it is the right tool.

Mitigation:
- keep asking what unique value eBPF adds
- compare mentally against simpler alternatives

### Risk 5: environment mismatch
There is a risk that WSL2 or the chosen path makes the first implementation harder than expected.

Mitigation:
- favor the simplest validation route
- treat technical obstacles as signals for scope adjustment

---

## 16. What “good progress” looks like

Good progress does not mean “finished.”

Good progress means:
- the problem statement becomes sharper
- the MVP becomes narrower and clearer
- assumptions become visible
- at least one practical implementation path becomes plausible
- one demo scenario becomes concrete
- one teammate-facing explanation becomes easier to write

---

## 17. Immediate next step

The single next step is:

> choose the narrowest practical v0 and turn it into an implementation-oriented plan.

That means the next design pass should focus on:
- candidate observation points
- event schema
- process filtering strategy
- request/response matching strategy
- latency measurement strategy
- one demo scenario

---

## 18. Current source-of-truth rule

For now:
- this brief is the source of truth for project framing and scope
- `specs/dns-watch/spec.md` is the place for future behavior-level requirements
- implementation details should follow the brief and must not silently expand scope beyond it
