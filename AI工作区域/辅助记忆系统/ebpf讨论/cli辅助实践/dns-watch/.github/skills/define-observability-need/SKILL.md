---
name: define-observability-need
description: Turn a vague observability idea into a clear problem statement, MVP, and validation plan.
---

# Purpose

Use this skill when the user has a vague idea related to observability, eBPF, DNS, TCP, process behavior, or debugging, but does not yet have a clear task definition.

# Instructions

You must help the user clarify the idea without blocking on missing details.

## Required output structure

Return these sections:

### Problem
Rewrite the idea as a simple, concrete problem.

### User
Who needs this? Be specific.

### Why now
Why is this worth doing?

### Why eBPF
Explain whether eBPF is justified here. If not fully justified, say so.

### MVP
Define the smallest useful version.

### Data to collect
List the exact fields that should be captured.

### Non-goals
List what is intentionally out of scope.

### Acceptance criteria
Define what “done” means for version 0.

### Open questions
List the unresolved product or implementation questions.

### Suggested next task
Propose the single next best step.

## Behavior rules
- Do not ask only clarifying questions. Also provide a draft answer immediately.
- Prefer a narrow scope over a broad one.
- If the user mixes business context and technical ideas, separate them clearly.
- If multiple MVP choices exist, show 2-3 options and recommend one.