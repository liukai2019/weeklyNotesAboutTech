Read these files first:
- .github/copilot-instructions.md
- docs/briefs/dns-watch-brief.md
- specs/dns-watch/spec.md
- dns-watch/prompts/kickoff.md

Assume kickoff has already been done or is being used as context.

Now refine dns-watch v0 into an implementation-oriented plan.

Goal:
Turn the current brief into the smallest believable implementation plan for v0.

Please do the following:

1. Restate the chosen v0 in one short paragraph.
2. Identify likely observation points or hook-point categories.
3. Propose the simplest practical implementation direction.
4. Define the event schema for v0.
5. Explain how process filtering should work in v0.
6. Explain how request/response matching could work in v0.
7. Explain how latency could be measured in v0.
8. Identify what should happen in kernel/eBPF space vs userspace.
9. Describe one realistic demo scenario.
10. Describe one verification approach.
11. List the top implementation risks and how to reduce them.
12. Break the work into 3 small phases:
    - phase 1: proof
    - phase 2: usable v0
    - phase 3: cleanup/polish

Important rules:
- Prefer the simplest believable v0, not the most complete design.
- Do not silently add downstream connect correlation into v0.
- If multiple technical paths exist, compare them briefly and recommend one.
- If WSL2 may affect feasibility, call that out explicitly.
- If some field in the brief is too ambitious for v0, say so clearly.

Use this output structure:

## Chosen v0 restatement
## Candidate observation points
## Recommended implementation direction
## Event schema
## Process filtering
## Request/response matching
## Latency strategy
## Kernelspace vs userspace split
## Demo scenario
## Verification approach
## Main risks and mitigations
## 3-phase plan
### Phase 1
### Phase 2
### Phase 3