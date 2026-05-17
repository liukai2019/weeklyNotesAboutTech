Read these files first:
- .github/copilot-instructions.md
- docs/briefs/dns-watch-brief.md
- specs/dns-watch/spec.md
- dns-watch/README.md
- dns-watch/TODO.md
- dns-watch/questions.md
- dns-watch/decision-log.md

Use the brief as the current source of truth for scope and framing.
Treat the spec as evolving unless it is clearly complete and aligned with the brief.

Session rules:
- do not silently expand scope
- keep uncertainty visible
- prefer small, testable, believable progress
- if proposing document changes, explain why
- if brief and spec differ, call it out explicitly
- prioritize teammate-readable output
- optimize for a solo engineer with limited time
- assume the environment is Windows 10 + WSL2 + Ubuntu
- keep v0 focused on DNS observation unless explicitly told otherwise

When answering:
- be concrete
- prefer narrow next steps
- separate must-have vs defer vs out-of-scope
- avoid pretending uncertain behavior is settled
- do not jump into large architecture unless asked

If the task is unclear:
- first restate the task simply
- then propose the smallest useful next step