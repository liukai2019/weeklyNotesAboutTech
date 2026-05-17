# TODO

## Clarify
- [x] Decide the narrowest useful v0 definition
- [x] Decide whether filtering is by pid, comm, or both
- [x] Decide whether child processes are explicitly out of scope for v0
- [x] Decide whether v0 requires query name extraction or whether that can partially degrade
- [x] Decide what counts as a “good enough” `resolver_call_latency_ms` signal for v0

## Design
- [x] Identify the simplest practical observation path in WSL2 Ubuntu
- [x] Choose one request/response matching strategy for v0
- [x] Define the v0 event schema
- [x] Define what happens in eBPF/kernel space vs userspace
- [x] Define one narrow demo scenario

## Implementation
- [x] Create the minimum project skeleton for dns-watch v0
- [x] Add one placeholder output format for the expected event stream
- [ ] Implement the smallest proof that target-process DNS activity can be observed
- [x] Implement a first pass of process filtering
- [x] Implement a first pass of request/response timing correlation
- [ ] Add one tiny hit-counter spike for the next resolver symbol under test

## Validation
- [x] Pick one repeatable test process for the demo
- [x] Create `scripts/demo.sh`
- [x] Create `scripts/verify.sh`
- [x] Capture one sample output
- [x] Write one short explanation of what the demo proves
- [x] Write one short explanation of what the demo does not prove
- [ ] Prove that at least one resolver-layer symbol actually fires for a controlled target PID

## Documentation
- [x] Keep `docs/briefs/dns-watch-brief.md` aligned with actual scope decisions
- [ ] Keep `specs/dns-watch/spec.md` limited to what is actually understood
- [x] Record scope decisions in `dns-watch/decision-log.md`
- [x] Record unresolved questions in `dns-watch/questions.md`
- [x] Record the root-mode validation outcome and the current `getaddrinfo()` blocker in `dns-watch/notes.md`

## Explicitly not in v0
- [ ] Do not add downstream `connect()` correlation
- [ ] Do not add returned IP analysis unless v0 proves it is necessary
- [ ] Do not add retry/alternate-IP logic
- [ ] Do not add dashboards, storage, or polished UX
- [ ] Do not silently expand scope beyond DNS observation

## Current blocker
- [ ] `libc:getaddrinfo()` uprobes create successfully under root but still show zero hits in the current WSL2 runtime tests
