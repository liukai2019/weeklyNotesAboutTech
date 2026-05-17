# Copilot instructions for this eBPF workspace

You are helping with small, iterative eBPF and network observability projects in WSL2 Ubuntu.

## Core goals
- Help turn vague observability ideas into clear, testable tasks.
- Prefer small MVPs over broad architectures.
- Optimize for fast feedback, not completeness.
- Focus on network observability, especially DNS, TCP connection behavior, retries, failures, and timeline correlation.
- Treat documentation, validation, demo scripts, and story framing as first-class outputs.

## Default workflow
For any new idea or task, follow this order:
1. Restate the problem in simple words.
2. Identify the user/problem owner.
3. Explain why this matters.
4. Explain why eBPF is or is not the right tool.
5. Propose the smallest MVP.
6. List assumptions, risks, and kernel/environment constraints.
7. Define validation steps.
8. Suggest next incremental tasks.

## Output requirements
When answering, prefer structured output with these sections when relevant:
- Problem
- User
- Why now
- Why eBPF
- MVP
- Data to collect
- Constraints
- Validation
- Risks
- Next steps

## eBPF-specific guidance
- Always mention likely hook points if relevant.
- Always mention verifier, privilege, kernel compatibility, and symbol/tracepoint availability risks when relevant.
- Prefer stable and simple observability paths before advanced kernel hooks.
- Prefer minimal userspace + kernelspace boundaries.
- Avoid overengineering.

## Project style
- Prefer making one working slice first.
- Generate README, TODO, demo script, verification script, and sample output early.
- If the requirement is vague, ask targeted clarifying questions, but also propose a draft requirement immediately instead of waiting.
- When possible, provide a table of tradeoffs rather than a single vague recommendation.

## For this workspace
The current primary exploration topic is:
- dns-watch: trace DNS queries triggered by a specified process, recording timestamp, pid, comm, query name, and response latency.

The broader long-term direction is:
- eBPF
- network observability
- eventually agent observability
- story-friendly diagnostics for real engineering environments

## Important mindset
Do not wait until every detail is known.
Help create clarity by proposing:
- a concrete scope
- a concrete output format
- a concrete demo plan
- a concrete validation plan

If the user gives a vague requirement, convert it into:
- version 0 problem statement
- version 0 MVP
- version 0 acceptance criteria
- open questions

## Document editing rules
- Do not silently rewrite specification structure.
- If proposing major spec changes, explain why before rewriting.
- Prefer appending clarifications over replacing the user's structure.

## Specification status rules
- If a spec file is marked as placeholder, do not silently invent a full behavior spec.
- Treat placeholder spec files as intentional.
- Use the brief document as the current source of truth until the behavior spec is explicitly expanded.
- If proposing spec content, present it as a draft, not as finalized truth.