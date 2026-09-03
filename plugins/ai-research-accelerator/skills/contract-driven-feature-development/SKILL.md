---
name: contract-driven-feature-development
description: Plan and deliver substantial software features through a concise contract, risk-routed implementation ownership, and proportionate independent review. Use for new algorithms, cross-module work, shared core paths, or changes with meaningful regression or scientific risk; skip this workflow for small local edits.
---

# Contract-Driven Feature Development

Use context isolation where it materially improves implementation or review
quality without turning development into a heavyweight process.

## Route by risk

Use this workflow for substantial features such as a new algorithm or backend,
cross-module behavior, changes to shared training/runtime paths, or work whose
failure could silently alter scientific results. Handle small, local,
well-covered edits directly.

Split mixed requests by risk before delegation. A small profile or parameter
change must not inherit the full workflow merely because the same request also
contains an independent backend or algorithm integration. Give each separable
risk unit its own focused candidate, tests, and review boundary.

## Own only the feature gate

This skill owns the **feature gate**: scientific/domain semantics, compatibility,
implementation, and focused review. The applicable domain skill owns any
production-base certification and final release/launch gate. Consume its current
certificate; do not independently repeat incident archaeology, launcher
publication, bundle generation, or remote acceptance here.

Before implementation, establish only the interfaces, invariants, and
behavior-level tests needed to make the feature correct. Do not generate final
release hashes, launch bundles, experiment identities, or deployment evidence
while the implementation is still changing. Produce those once, after the
candidate passes the feature gate.

## Freeze a concise contract

The main thread is the coordinator. Before implementation or review, write a
compact contract that contains only what the selected owner needs:

- the objective and explicit non-goals;
- the frozen base commit and authoritative implementation references;
- for runtime/backend/algorithm work, the latest accepted production-runtime
  manifest, its canonical base commit, applicable promoted fixes, and any
  explicitly pending incident repair;
- existing behavior and scientific or compatibility invariants that must not
  change;
- allowed ownership boundaries, expected feature switch, and any shared paths
  that are frozen unless a contract amendment is approved;
- behavior-level tests and acceptance evidence required for completion;
- permissions and actions that remain outside the Agent's authority.

Keep the contract short enough to inspect quickly. Do not perform broad code
archaeology by default. Expand investigation only when code, tests, and known-good
evidence contradict one another.

Do not choose a stale repository `main` merely because it is easy to branch.
For runtime/backend/algorithm work, require the production-base certificate from
the owning domain skill before branching. If new incidents invalidate it, let
that owner incrementally promote the applicable operational deltas and issue a
new certificate. Do not duplicate that audit inside this workflow. If promotion
is intentionally deferred, it is a declared blocker rather than work silently
delegated to the implementation or training-node Agent.

## Choose the implementation owner

Default to the main Agent when its context is coherent, the ownership boundary
is clear, and it can implement the candidate directly. A substantial label alone
does not justify paying the context-reconstruction and integration cost of a
fresh implementer.

Use one fresh-context implementation Agent when at least one concrete condition
applies: the main context is demonstrably degraded or contradictory; the work is
a large separable backend or subsystem with a compact handoff; or parallel
ownership materially shortens the critical path without sharing mutable files.
Give that Agent the contract, necessary source files, and authoritative
references, and let it work in an isolated worktree at the frozen base commit.

Whichever Agent implements the feature must:

- keep new behavior additive and behind an explicit switch when existing
  behavior must remain available;
- avoid shared-core edits unless the contract allows them;
- request a contract amendment instead of silently expanding scope;
- add tests that execute meaningful behavior, not tests that merely match
  source strings or expected wording;
- leave a focused diff and a reproducible test report.

## Review in proportion to risk

Small, local, well-covered changes need no independent reviewer when targeted
behavioral tests and frozen regressions directly establish correctness. For a
new algorithm/backend, shared-core change, or scientifically silent failure
risk, use one fresh-context reviewer after the candidate is stable. Provide the
contract, final diff, authoritative references, and test results, but do not
provide the implementer's reasoning, desired verdict, or suspected findings.

One reviewer is the default ceiling. Add a second only when the first review
exposes a genuinely separate expert domain, leaves a material disputed finding,
or the resulting fix changes the contract or architecture. Do not run several
reviewers in parallel merely to increase confidence; behavioral tests and
primary references are the evidence base.

The reviewer checks, in this order:

1. algorithm or domain semantics against the contract and references;
2. regressions in frozen behavior and default-off feature isolation;
3. changes to shared paths, ownership boundaries, and runtime contracts;
4. whether the candidate contains every applicable promoted production fix and
   the feature did not regress its behavioral test;
5. whether tests exercise the failure-prone behavior and realistic topology;
6. remaining evidence gaps.

Report findings first with concrete file references. The implementation owner
addresses findings; the reviewer does not silently redefine the contract.

When the risk route requires independent review, review the stable candidate
once. After localized fixes, verify the reported findings and affected
regressions; do not restart an unbounded full review unless the contract,
architecture, or frozen behavior changed materially.

## Integrate in the main thread

The main thread resolves contract questions, confirms material review findings
are closed, and runs the smallest sufficient acceptance set: targeted new-feature
tests and frozen-path regressions. Reuse the owning domain skill's valid
production-base certificate rather than rerunning its audit. The final release
gate may add the production-runtime validator and one real smoke only when
hardware, distributed, or external-service behavior cannot be validated
locally. Avoid duplicated reviews, repeated full suites, and repeated smoke runs
without a changed contract or invalidated certificate.

Do not claim an independent review was completed when a required fresh reviewer
was unavailable. A fresh Agent is context-isolated, not context-free: omitting
the contract or known-good evidence reduces independence to guesswork.
Delegation never expands the user's permissions or authorizes unrelated changes.
