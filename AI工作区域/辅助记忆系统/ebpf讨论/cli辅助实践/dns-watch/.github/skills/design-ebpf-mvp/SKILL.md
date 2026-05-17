---
name: design-ebpf-mvp
description: Design a minimal eBPF-based implementation plan for a small observability tool.
---

# Purpose

Use this skill when the user already has a rough observability need and wants a practical implementation plan.

# Instructions

Design a minimal implementation, prioritizing simplicity, debuggability, and fast validation.

## Required output structure

### Goal
State the exact MVP goal.

### Candidate hook points
List likely kernel/user-space observation points.

### Recommended approach
Choose one approach and explain why.

### Data flow
Describe:
1. where data is observed
2. how it is filtered
3. how it is transferred to user space
4. how it is rendered

### Event schema
List the event fields.

### Userspace responsibilities
List what userspace should do.

### Kernel/eBPF responsibilities
List what eBPF code should do.

### Filtering strategy
Explain how process filtering should work.

### Timing/latency strategy
Explain how latency should be measured.

### Validation plan
Describe a demo and expected output.

### Risks
List likely failure points:
- verifier
- unavailable hooks
- DNS parsing complexity
- privilege requirements
- WSL2/kernel constraints
- library compatibility

### Phase split
Break the work into 3 phases:
- phase 1: minimum proof
- phase 2: usable tool
- phase 3: polish or upstream readiness

## Behavior rules
- Prefer the simplest thing that can work.
- If implementation choices are uncertain, say so explicitly.
- Do not jump to advanced architecture unless necessary.
- Mention tradeoffs.