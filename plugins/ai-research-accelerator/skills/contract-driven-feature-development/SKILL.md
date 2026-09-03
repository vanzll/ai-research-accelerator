---
name: contract-driven-feature-development
description: Plan and deliver substantial software features through a coordinator-authored contract, a fresh-context implementation agent, and an independent fresh-context reviewer. Use for new algorithms, cross-module work, shared core paths, or changes with meaningful regression or scientific risk; skip this workflow for small local edits.
---

# Contract-Driven Feature Development

Use context isolation to improve implementation and review quality without
turning development into a heavyweight process.

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

The main thread is the coordinator. Before delegation, write a compact handoff
that contains only what a fresh Agent needs:

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

## Delegate implementation to a fresh context

Launch an implementation Agent with no inherited conversational history. Give
it the contract, necessary source files, and authoritative references, and let
it work in an isolated worktree at the frozen base commit.

The implementation Agent must:

- keep new behavior additive and behind an explicit switch when existing
  behavior must remain available;
- avoid shared-core edits unless the contract allows them;
- request a contract amendment instead of silently expanding scope;
- add tests that execute meaningful behavior, not tests that merely match
  source strings or expected wording;
- leave a focused diff and a reproducible test report.

## Review from an independent fresh context

Use a different fresh Agent for review. Provide the same contract, the final
diff, authoritative references, and test results, but do not provide the
implementer's reasoning, desired verdict, or suspected findings.

The reviewer checks, in this order:

1. algorithm or domain semantics against the contract and references;
2. regressions in frozen behavior and default-off feature isolation;
3. changes to shared paths, ownership boundaries, and runtime contracts;
4. whether the candidate contains every applicable promoted production fix and
   the feature did not regress its behavioral test;
5. whether tests exercise the failure-prone behavior and realistic topology;
6. remaining evidence gaps.

Report findings first with concrete file references. The implementation Agent
addresses findings; the reviewer does not silently redefine the contract.

Use one independent review of the stable candidate. After localized fixes,
verify the reported findings and affected regressions; do not restart an
unbounded full review unless the contract, architecture, or frozen behavior
changed materially.

## Integrate in the main thread

The main thread resolves contract questions, confirms material review findings
are closed, and runs the smallest sufficient acceptance set: targeted new-feature
tests and frozen-path regressions. Reuse the owning domain skill's valid
production-base certificate rather than rerunning its audit. The final release
gate may add the production-runtime validator and one real smoke only when
hardware, distributed, or external-service behavior cannot be validated
locally. Avoid duplicated reviews, repeated full suites, and repeated smoke runs
without a changed contract or invalidated certificate.

Do not claim this workflow was completed when fresh contexts were unavailable.
A fresh Agent is context-isolated, not context-free: omitting the contract or
known-good evidence reduces independence to guesswork. Delegation never expands
the user's permissions or authorizes unrelated changes.
