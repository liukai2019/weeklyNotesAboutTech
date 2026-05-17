Read these files first:
- .github/copilot-instructions.md
- docs/briefs/dns-watch-brief.md
- specs/dns-watch/spec.md

Use the current brief as the main source of truth.
Treat the spec as partial or evolving unless it is already clearly filled in.

I want you to help me narrow dns-watch into the smallest practical v0.

Please do the following in order:

1. Restate the project in simple words.
2. Identify the narrowest useful v0 problem statement.
3. List the exact fields that v0 should output.
4. Separate:
   - must-have for v0
   - nice-to-have but defer
   - out of scope
5. Identify the main ambiguities that still remain.
6. Propose 2 implementation directions for v0.
7. Recommend the simpler one.
8. Explain why that recommendation best fits:
   - limited time
   - WSL2 Ubuntu environment
   - current eBPF/libbpf learning stage
   - need for readable, teammate-friendly output
9. End with:
   - a one-paragraph v0 definition
   - a short acceptance checklist
   - the single next implementation step

Important rules:
- Do not silently expand scope from DNS observation into full DNS-to-connect correlation.
- Do not assume all future features belong in v0.
- If the spec and brief differ, call out the difference explicitly instead of guessing.
- Prefer a small, testable, believable MVP over a more impressive design.
- If something is uncertain, say so clearly.

Use this output structure:

## Simple restatement
## Narrowest useful v0
## v0 output fields
## Scope split
### Must-have
### Defer
### Out of scope
## Remaining ambiguities
## Two implementation directions
### Option A
### Option B
## Recommended direction
## One-paragraph v0 definition
## v0 acceptance checklist
## Single next implementation step