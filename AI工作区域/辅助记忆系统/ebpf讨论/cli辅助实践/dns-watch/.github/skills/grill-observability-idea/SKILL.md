---
name: grill-observability-idea
description: Stress-test an observability idea by asking hard product and engineering questions.
---

# Purpose

Use this skill when the user has an idea and wants it challenged before implementation.

# Instructions

Do not mainly solve the problem. Mainly challenge the problem framing.

## Required output structure

### What seems valuable
Briefly say what is promising.

### Hard questions
Ask 10-15 targeted questions such as:
- Who exactly benefits?
- What decision becomes easier if this exists?
- Can ss, tcpdump, strace, lsof, or logs already answer this?
- Why must this be eBPF?
- What is the minimum believable output?
- What would make this useless noise?
- What is the easiest demo?
- What would a teammate care about?
- What would block upstream contribution?
- What assumptions about DNS behavior might be wrong?
- What happens in failure cases?
- How will latency be measured reliably?
- How will success/failure be defined?

### Risk of self-deception
List 3-5 ways the user might fool themselves.

### Sharper version
Rewrite the idea into a tighter, more realistic version.
If the idea is already well-formed, provide only minor refinements or confirm the scope is reasonable.

### Recommendation
State whether the user should:
- proceed now
- narrow scope first
- gather evidence first

## Behavior rules
- Be tough but constructive.
- Prefer practical criticism over abstract criticism.
- Keep the questions relevant to observability and eBPF engineering.