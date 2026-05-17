# Notes

## Working assumptions
- Start small.
- Do not require full DNS protocol coverage in v0.
- Prefer useful signal over completeness.
- A readable event stream is more important than a polished UI.

## Questions to revisit
- How well does WSL2 support the intended eBPF path?
- Are UDP and TCP DNS both needed in v0?
- How should query-response correlation be done?
- How much DNS parsing should happen in kernel vs userspace?

## Environment findings
- WSL2 kernel is `6.6.114.1-microsoft-standard-WSL2`, which is new enough to make the chosen v0 path plausible.
- `libc.so.6` exports `getaddrinfo`, so the intended userspace symbol target exists.
- `bpftool` is available in the environment.
- Current user access is the immediate constraint: `unprivileged_bpf_disabled=2`, `perf_event_paranoid=2`, and `/sys/kernel/tracing/uprobe_events` is not accessible as the current user.
- In practice, the first real attach attempt will likely need elevated privileges.

## Current implementation state
- `dns-watch` now builds as a minimal v0 skeleton.
- The current code path is: libc `getaddrinfo()` uprobe + uretprobe, same-thread pairing, PID filter in BPF, plain-text userspace output.
- `scripts/demo.sh` and `scripts/verify.sh` are ready for the first real privileged run.
- Non-root runtime currently fails early at `RLIMIT_MEMLOCK: Operation not permitted`, which matches the expected privilege constraint.

## Root-mode validation findings
- Running as root removes the earlier memlock/load permission blocker.
- `dns-watch` successfully loads, resolves the libc `getaddrinfo` symbol, and creates uprobe + uretprobe links.
- A baseline control test with `libbpf-bootstrap/examples/c/uprobe` proves that uprobes work in this WSL2 environment in general.
- Controlled tests against a fixed PID that `exec`s Python `socket.getaddrinfo("example.com", 80)` still produce zero hits in the `dns-watch` BPF stats map.
- This means the current blocker is not root permission anymore; it is the chosen libc `getaddrinfo()` observation path.

## Current likely blocker
- The current libc shared-library `getaddrinfo()` probe target appears not to fire in this environment, even though link creation succeeds.
- Possible causes still open:
  - shared-library symbol / offset handling for this libc build
  - the exact function symbol chosen for name resolution
  - a need to move to a different DNS observation point for v0

## Session recap
- We first suspected a privilege problem because the unprivileged user hit `RLIMIT_MEMLOCK: Operation not permitted`.
- After switching to a root shell, that specific blocker disappeared.
- The `dns-watch` loader could then:
  - load the BPF object
  - resolve the `getaddrinfo` symbol in libc
  - create uprobe and uretprobe links successfully
- That changed the diagnosis:
  - before root: blocked at privilege / load time
  - after root: blocked at observation / symbol-hit time

## What was explicitly proved
- Root is required for the current WSL2 setup.
- Root is sufficient for:
  - memlock setup
  - BPF load
  - BPF link creation
- Uprobes are not fundamentally broken in this environment.
- The current `libc:getaddrinfo` path is the part that still lacks evidence.

## What was explicitly not proved
- We did not prove that `curl http://example.com` produces a readable `dns-watch` event yet.
- We did not prove that libc `getaddrinfo()` is the right v0 observation point on this machine.
- We did not prove packet-level DNS visibility.
- We did not prove returned IP capture, DNS success/failure semantics, or downstream `connect()` correlation.

## Concrete debugging observations
- `timeout ./dns-watch ...` introduced some confusing behavior during early checks, so later tests used more direct command control.
- A fixed-PID shell plus `exec python3 -c 'import socket; socket.getaddrinfo("example.com", 80)'` was used to avoid PID ambiguity.
- Extra BPF stats counters were added temporarily to distinguish:
  - probe link exists
  - probe handler runs at all
  - PID filter passes
- Those counters stayed at zero, which strongly suggests the current probe target is not being hit.
- Changing from global attach plus BPF PID filtering to PID-specific attach did not change the result.
- Changing libc path from `/lib/x86_64-linux-gnu/libc.so.6` to the resolved file `/usr/lib/x86_64-linux-gnu/libc-2.31.so` did not change the result.

## Candidate next observation points
- Prefer trying symbols in `libresolv.so.2` next instead of continuing to spend time on libc `getaddrinfo()`.
- Current candidate order:
  1. `__res_context_search`
  2. `__res_nsearch`
  3. `__res_nquery`
  4. `__res_send` if the higher-level resolver functions still do not fire

## Why the recommendation changed
- The original v0 plan chose `getaddrinfo()` because it was easy to explain and matched the desired field semantics.
- The runtime evidence now suggests that “easy to explain” is not enough if the chosen hook point does not actually fire.
- Because baseline uprobes work, the most efficient next step is to change hook point, not to keep re-debugging root or generic uprobe support.

## Recommended next experiment
- Build a minimal spike that does only one thing:
  - attach to one `libresolv.so.2` candidate symbol
  - count hits for one controlled target PID
- Do not preserve the full v0 event output in that spike.
- First prove hit/no-hit.
- Only after a hit is confirmed should query-name extraction and readable event formatting be wired back in.

## Root-shell handoff
- `copilot` absolute path: `/mnt/c/Users/kai.liu/AppData/Roaming/npm/copilot`
- Recommended root-shell start:
  `/mnt/c/Users/kai.liu/AppData/Roaming/npm/copilot`
- After Copilot starts in the root shell, the first command to run is:
  `cd /home/kk2018/ebpf/dns-watch && ./scripts/demo.sh`
- Or for the stricter check:
  `cd /home/kk2018/ebpf/dns-watch && ./scripts/verify.sh`
