---
name: contract-driven-feature-development
description: Coordinate substantial feature work across coding agents through concise contracts and durable handoffs. Use for new algorithms, separable cross-module work, shared-core changes, or real runtime repairs; skip for small local edits.
---

# Contract-Driven Feature Development

Use this skill to coordinate agents, not to teach a capable coding agent how to
program. Ordinary implementation choices, local refactors, and routine tests
belong to the implementation owner.

## Choose the lightest route

- Handle a small, local, well-covered change directly in the current Agent.
- Use a fresh implementation Agent only when the main context is degraded, the
  work is a large separable subsystem, or parallel ownership clearly shortens
  the critical path. Give it an isolated worktree and a compact handoff.
- A parameter-only experiment must not inherit the workflow for a new backend
  merely because both appear in one request.

The main Agent remains coordinator and integrator. Delegation does not expand
permissions or silently broaden the feature.

## Write a concise handoff

Give another Agent only the information needed to make the intended change:

- objective and explicit non-goals;
- frozen base commit and authoritative references;
- scientific, behavioral, and compatibility invariants that must remain true;
- ownership boundary and the switch that isolates new behavior;
- observable acceptance evidence;
- actions outside the Agent's authority.

Do not make the recipient repeat broad repository archaeology when the main
Agent already knows the relevant paths and accepted baseline. Amend the handoff
only when evidence changes the contract.

## Preserve cross-agent history

When implementation is later exercised by a remote Goal Agent, connect the two
Agents through durable repository evidence rather than chat memory. The remote
record should identify:

- the exact commit and secret-free command supplied by the coding Agent;
- observed failures and primary evidence;
- the exact successful commit and command, if the remote Agent repaired code;
- the relevant Git delta, tests, and whether scientific semantics changed.

Before the next related implementation or prompt, the main Agent reads only new
records since its watermark, verifies material claims against Git/logs/results,
and promotes applicable operational fixes into the canonical code. Use
`continuous-skill-learning` for this evidence loop. A remote explanation is an
index, not proof.

## Review only when justified

Independent review is not the default. Use at most one fresh reviewer when:

- the user explicitly requests review;
- the change introduces a new algorithm or backend whose semantics can fail
  silently; or
- a real runtime incident required a shared-core or architectural repair.

Review the stable executable code candidate before producing release metadata.
Ask the reviewer for concrete blocking findings against the contract, not a
broad redesign. After localized fixes, verify those findings and affected
behavior; do not restart an unbounded full review unless the contract or
architecture changed materially.

## Finish efficiently

Run the smallest tests that establish the changed behavior and protect affected
frozen paths. Reuse valid domain/runtime evidence when its inputs are unchanged.
Generate deployment hashes, bundles, manifests, and prompts once, after the code
candidate is stable, and only when the repository's established release process
or the user requires them. If executable source changes afterward, regenerate
only the invalidated artifacts.
