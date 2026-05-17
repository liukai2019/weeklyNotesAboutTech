# Open questions

## Product / usefulness
- What is the narrowest useful definition of dns-watch for v0?
- Is query name alone enough for first usefulness?
- What is the minimum output that would be useful to a teammate?
- What would make the output technically correct but practically unhelpful?

## Scope
- Should filtering be by pid, comm, or both?
- Should child processes be in scope for v0?
- Should v0 support only one straightforward DNS path?
- Is partial degradation acceptable if query name extraction fails in some cases?

## Technical
- What are the main environment constraints in WSL2 for this idea?
- What are the important limitations of the `getaddrinfo()` uprobe/uretprobe path in WSL2 Ubuntu?
- How much parsing should happen before data is emitted?
- Is `RLIMIT_MEMLOCK` plus uprobe attach consistently available under the intended sudo flow in this WSL2 setup?
- How often do overlapping or nested `getaddrinfo()` calls on the same thread matter for real targets?
- Do alternate resolver paths or statically linked binaries reduce the usefulness of the libc `getaddrinfo()` path too much for v0?
- Which `libresolv.so.2` symbol is the best next hook for a hit/no-hit spike: `__res_context_search`, `__res_nsearch`, `__res_nquery`, or `__res_send`?
- If `libresolv.so.2` hooks fire, how much query-name extraction can be recovered without overloading v0?
- If only `__res_send` fires reliably, is it still acceptable to keep v0 focused on one readable story, or does that force an explicit scope adjustment?

## Demo / validation
- Does the `sleep 2; exec curl ...` demo remain reliable enough to prove the first narrow story?
- What exact failure message should be treated as the expected non-root outcome in this environment?
- What is the smallest controlled target process for future hook testing: Python `socket.getaddrinfo()`, a tiny C resolver test, or `curl`?
- Should the next validation spike prove only counter hits first, before restoring the full human-readable event line?

## Future expansion
- When should returned IP addresses be added?
- When should DNS success/failure be represented explicitly?
- Under what conditions would downstream `connect()` correlation become worth adding?
- What evidence would justify moving from v0 to v1?
