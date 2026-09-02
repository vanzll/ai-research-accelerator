---
name: manage-paper-experiments
description: Manage formal ML paper experiments from planning through reproducible reporting. Use when building or auditing the paper-wide experiment ledger, assigning paper experiment IDs, freezing code and protocols, scheduling GPU-node queues or waiters, generating send-and-forget remote Codex prompts, monitoring and reconciling W&B runs, retaining best/final checkpoints, or preparing paper curves and result tables.
---

# Manage Paper Experiments

Treat the experiment ledger as the single source of truth. Convert the paper plan into uniquely identified, reproducible runs; carry each run through scheduling, execution, W&B reconciliation, checkpoint retention, and paper reporting without silently changing the protocol.

## Start With Context

1. Read the applicable `AGENTS.md` before any local or remote action.
2. Locate and read the paper `plan.md`, experiment ledger, repository progress document, and relevant launcher/config files.
3. Read [ledger-schema.md](references/ledger-schema.md) before changing experiment state.
4. Read [queue-patterns.md](references/queue-patterns.md) before producing remote prompts or launch commands.
5. Read [reporting-protocol.md](references/reporting-protocol.md) before comparing runs or filling paper tables.
6. When installed, use `wandb-query` for W&B config, summary, history, state, and workspace inspection. Otherwise use an authorized API/export and record the evidence gap. Do not infer results from a run name or reward plot alone.

If the plan and ledger disagree, stop scheduling affected experiments and surface the conflict. Do not invent extra seeds, ablations, evaluators, or method changes.

## Preserve Two Evidence Surfaces

Always track these separately:

- **Training dynamics:** speed, stability, threshold-crossing steps, peak, final, tail mean, drawdown, reward calls, and GPU-hours.
- **Held-out evaluation:** pre-registered evaluation steps, best evaluation on a shared grid, selected step, final evaluation, evaluator identity, and checkpoint identity.

Never substitute train reward for evaluation, or a train peak for best evaluation. A stopped or collapsed run may be valid stability evidence while remaining invalid as a completed evaluation result.

## Maintain a Paper-Wide Evidence Index

The ledger is the complete experiment record for the paper, not a queue tracker. A future writer must be able to recover the paper's experiment coverage and every paper-facing result without chat history.

- Map every `plan.md` item to one of: formal run, baseline run, historical evidence, optional, invalidated, protocol conflict, or genuinely missing.
- For every attempt record completion state, W&B display name, run ID and URL, a compact result summary, evaluator, checkpoint when applicable, and protocol caveat.
- Index historical runs even when they lack formal IDs. Mark them curve-only or mechanism-only, record train peak/final/tail/drawdown, and write `no held-out eval` rather than leaving evaluation ambiguous.
- Keep a compact headline-results table, a complete attempt registry, and a claim-oriented historical evidence table. These are complementary views of the same evidence.
- Before saying that no more experiments are needed, reconcile the entire plan and list required gaps, optional gaps, items resolved by history, and unresolved protocol conflicts.
- When discussion adds, removes, or changes a proposed experiment, update the plan-coverage and attempt rows immediately, before launch code is written. A discussed experiment must not live only in chat.
- When asked to update or report the ledger, query W&B config, summary, state, and targeted history first. Never copy stale status or results from memory, tmux names, local logs, or an earlier ledger snapshot when W&B is available.

Do not force every exploratory run into the ledger. Include it when it supports a paper claim, appears in a planned figure/table/ablation, resolves a planned item, or explains why an experiment was excluded.

## Lifecycle

### 1. Derive the Experiment Matrix

- Translate the paper claims into the smallest set of decisive comparisons.
- Mark each experiment as main-table, curve-only, diagnostic, appendix, baseline, or invalidated.
- Require a unique paper experiment ID and attempt number before launch.
- Keep method, model, benchmark, seed, budget, evaluation grid, and checkpoint policy explicit.
- Reuse existing valid runs only after checking their exact config and protocol compatibility.
- Build and maintain an explicit plan-coverage matrix. A plan item is not covered merely because a similarly named run exists.

Do not broaden the matrix merely because capacity is available. Additional seeds or ablations require support from the plan or explicit user approval.

### 2. Define Observability Before Launch

Brainstorm and confirm informative W&B metrics before writing a launcher. At minimum consider:

- train reward, held-out evaluation, and all reward components;
- total/objective loss, advantage scale and distribution, ratio/clip/KL metrics;
- raw and clipped gradient norms, parameter update norm, learning-rate scale;
- output/function movement, guidance/restore scale and cosine, per-timestep diagnostics;
- rollout diversity, tie/validity fractions, prompt/group statistics;
- wall time, GPU-hours, rollout count, reward calls, and failure diagnostics.

Only add metrics that can distinguish the experiment's hypotheses. State what each critical metric diagnoses.

### 3. Freeze the Run Contract

Before scheduling:

- freeze the exact commit SHA, launcher/config, dependencies, seed, budget, W&B project/group/tags, and experiment ID;
- maintain one repository-root incident index under `踩坑记录/`, and assign the
  attempt a structured record there plus any absolute shared-storage evidence
  path needed for large logs; keep the control checkout separate from the clean
  detached runtime worktree;
- freeze the expected W&B display name or deterministic name pattern and the startup handshake fields that will identify the run;
- specify evaluation steps and whether best selection uses a shared grid;
- specify final and best checkpoint retention, pruning, and disk limits;
- run targeted config/objective tests, compilation checks, and shell syntax checks;
- ensure the W&B fail-open mechanism does not convert training success into an untraceable run;
- record the immutable contract in the ledger.

Changes after launch create a new attempt. Never overwrite the identity of an existing attempt.

For matched sibling experiments intended to differ by one scientific variable,
freeze one shared operational commit as part of the comparison. If a retry
discovers an operational repair in either sibling, integrate and validate that
repair in the common runtime before launching further siblings; do not let each
treatment accumulate its own launcher, synchronization, telemetry, memory, or
distributed-lifecycle patch chain. Until all compared runs use the same repaired
runtime, label the evidence operationally confounded and do not attribute a
success, failure, or metric difference to the intended scientific variable.

### 4. Schedule From Actual Capacity

- Inspect the node hostname, active queues, training processes, GPU use, reservations, and success markers.
- Respect the capacity rules recorded in the plan/ledger; do not assume every eight-GPU node has identical concurrency.
- Never launch GPU work on a development-only host.
- Bind every prompt to an exact hostname and fail closed on mismatch.
- Prefer persistent tmux queues or waiters so the remote Codex does not need to remain active.
- For concurrent jobs, the outer queue owns `gpu_free` and the final `gpu_hold`; child jobs must not release GPUs while siblings remain active.

The queue must wait on both process completion and the expected success marker. Process exit alone is not proof of a valid completed experiment.

### 5. Launch Reproducibly

On a training node:

1. Source the required environment bootstrap.
2. Verify `hostname -f`.
3. Materialize a clean, node-specific checkout at the exact commit.
4. Refuse dirty tracked files, wrong commits, duplicate reservations, or an occupied experiment ID.
5. Run the preflight tests.
6. Start the persistent queue with logs, reservation, W&B identity, checkpoint path, and success marker recorded.
7. Verify the first W&B history/config rows before considering the launch complete.

Follow the project's exact `gpu_free`/`gpu_hold` contract. A direct command must restore the hold through a trap on success, failure, or crash.

## Send-and-Forget Remote Delegation

A remote Coding Agent prompt must be self-contained and bootstrap a durable,
token-free supervisor. Read [queue-patterns.md](references/queue-patterns.md)
whenever producing such a prompt.

The operating standard is literal: after sending the prompt, the user must be
able to stop watching the node. This does **not** mean the Coding Agent remains
active for hours. The agent performs bounded bootstrap and exits; a tmux/shell
supervisor owns waiting, stage transitions, retries, markers, and GPU cleanup.
Long-lived agent polling is a workflow failure and wastes tokens.

Do not send a remote Goal prompt as a substitute for finishing the launcher.
First require the applicable `multinode-training` one-shot readiness evidence
and freeze the tested command; the remote Agent should primarily execute,
attest, and hand off that command. Its bounded bug-fix authority and
retrospective capture unexpected environment failures, but they are not the
default implementation or debugging strategy.

Unless the user explicitly asks only for discussion or a draft, asking for an
experiment prompt includes finishing the code/config/launcher, incrementally
reconciling new `踩坑记录/` entries, promoting applicable repairs with behavioral
regressions, validating an already certified production runtime, committing and
pushing the candidate, and generating an immutable launch bundle. Emit the
prompt only for that remotely reachable full commit and bundle hash.

Choose one orchestration mode before launch:

- **Deterministic formal queue:** when all experiments and dependencies are
  frozen, a shell supervisor launches every stage, verifies startup/completion
  markers, retries pre-authorized infrastructure failures, and finishes without
  waking Codex.
- **Event-driven research relay:** when promotion or diagnosis requires model
  judgment, a mechanical watcher observes logs/progress and wakes the exact
  Codex thread only on a milestone, stale heartbeat, process exit, or fatal
  signal. The watcher never analyzes results or changes the queue. Codex handles
  one event, updates state, re-arms the watcher, and exits. Use the bundled
  `long-task-relay` skill and its standard-library CLI instead of creating a
  project-specific polling loop. Experiment-specific supervisors may add W&B
  and GPU lifecycle checks around this generic relay contract.

Never emulate either mode with a Codex loop that sleeps and polls.

- Include exact hostname and either all frozen launch details or an immutable
  launch-bundle path plus SHA256. The bundle contains repository/source
  checkout, full SHA, tests, queue command, experiment IDs, expected W&B names,
  logs, markers, and recovery boundaries. Never refer to an earlier prompt or
  assume the remote Agent remembers prior context.
- Include the root incident record and literal external evidence path. Require
  the remote Agent to update them
  after each diagnosed retry and before Goal completion or blocking with the
  failed stage, primary evidence, root cause/confidence, original prompt
  commit/command, successful runtime commit/command, exact Git delta, optional
  later docs-only commit, semantic/config impact, validation, and remaining
  uncertainty. The prompt must not leave these lessons only in the remote
  conversation.
- Do not define bootstrap success as “command returned” or “reservation
  created”. The agent must verify the persistent supervisor, its durable
  heartbeat/log, frozen environment, queue contract, and GPU cleanup trap.
- If the first stage launches immediately, the agent must remain only through
  that stage's W&B startup handshake. If the queue is waiting on another job,
  verify the wait condition and supervisor heartbeat, then exit without polling
  until the dependency clears.
- Define the attempt boundary by evidence, not by whether a launcher process was invoked. Before W&B identity exists and while optimizer execution can be ruled out, environment activation, executable resolution, import, checkout transport, port, or logger-initialization failures are pre-start infrastructure failures. Archive their diagnostics, repair them, allocate the next pre-authorized attempt ID when identities or reservations were already exposed, and continue without returning control to the user.
- Activate the training environment inside the final persistent shell or tmux command. Verify the resolved Python and launcher executables plus required imports in that same shell before releasing `gpu_hold`; activation in the parent shell is not evidence that a child tmux inherited it. For editable/local packages, also verify each imported `__file__` resolves inside the frozen checkout. A successful import from an older editable worktree is a failed preflight.
- If another job blocks the node, create a durable waiter/supervisor, verify its
  command, environment preflight, heartbeat, dependency predicate, and recovery
  policy, then exit. The supervisor, not Codex, must launch and verify the later
  W&B handshake.
- Never hide a real attempt failure. Once a run exists or optimizer work may have occurred, preserve logs/reservations, allocate a new attempt ID for retry, update the ledger, and continue under the new lineage rather than overwriting evidence.
- For sequential queues, the wrapper must verify every later stage and write
  atomic startup/completion/failure markers. Codex validates this control flow
  before launch; it must not stay resident to witness stages that begin hours
  later.
- The prompt may finish after bounded bootstrap: the immediate stage has a valid
  W&B handshake, or a waiting supervisor has a fresh heartbeat and validated
  launch contract. Report the expected future marker paths so a later session
  can reconcile them without chat history.

### 6. Monitor and Reconcile

For every running experiment:

- confirm that the W&B config matches the frozen contract;
- when analyzing a W&B run or maintaining its ledger row, read the attempt's
  remote retrospective before drawing conclusions, reconcile its claims with
  logs/code/W&B, and run `continuous-skill-learning` on verified reusable
  lessons;
- update the root incident index with its reviewed and code-promotion
  disposition; prose review does not close a code repair, and a related prompt
  remains blocked while an applicable repair is pending outside canonical main;
- inspect summary and history, including per-update and per-timestep diagnostics;
- distinguish a stalled logger from a stalled trainer;
- compare progress using the pre-declared horizontal axis;
- update ledger state, latest step, W&B URL, host, queue, and anomalies;
- record the exact W&B display name as well as run ID/URL so the experiment remains searchable after remote context is lost;
- retain failures and explain whether they are valid evidence, infrastructure failures, or invalid configurations.

Normalize all heartbeat times before diagnosing staleness. Compute log age from
epoch timestamps on one host (for example, `date +%s` against `stat -c %Y`) and
record the timezone explicitly; never compare a remote UTC mtime string with a
local-time clock. Allow small cross-host clock skew. A W&B run that pauses
during reward/evaluation work is not stalled when its local log or optimizer
step continues to advance.

Do not stop, restart, or delete unrelated jobs. Do not silently relaunch a failed attempt under the same ID.

### 7. Close the Attempt

An attempt is complete only when its declared completion contract is satisfied. Record:

- exit and termination status;
- final training step and wall/GPU time;
- W&B run ID and state;
- best evaluation value and step on the allowed grid;
- final evaluation value and step;
- best and final checkpoint paths or artifacts;
- logs, success marker, and any data-quality caveat.

Then update the next queue from the ledger, not from memory.

### 8. Produce Paper Results

- Compare curves under matched W&B-step/reward-call/GPU-hour semantics declared by the paper.
- Report best evaluation only on the pre-registered shared grid, and report final evaluation alongside it.
- Include termination status so active stopping or collapse is visible.
- For multi-reward runs, preserve the aggregate and every component metric.
- Exclude invalidly configured baselines; document the exclusion rather than hiding the run.
- Keep historical and formal runs visibly distinct.
- Ensure every plotted/table result has a ledger row with a W&B link and compact result summary, and every ledger headline number identifies whether it is train, held-out eval, best, or final.

Use [reporting-protocol.md](references/reporting-protocol.md) for table fields and edge cases.

## Fail-Closed Conditions

Do not launch or advance a dependent queue when any of these applies:

- hostname, branch, commit, launcher, or frozen config does not match;
- tracked checkout is dirty or the exact commit cannot be materialized;
- experiment ID, W&B run, reservation, port, or output directory conflicts;
- prior queue lacks its required success marker;
- step semantics, evaluation grid, or checkpoint policy is ambiguous;
- required test or preflight validation fails;
- disk capacity is insufficient for the declared retention policy;
- another active process would violate the node's capacity contract.

Infrastructure uncertainty is not permission to improvise a semantically different experiment.
Fail closed means preserve the frozen scientific contract while repairing infrastructure; it does not mean hand a routine setup failure back to the user. Return blocked only when recovery would require a protocol/code-contract change, destructive action outside the owned scope, unavailable hardware after the declared retry window, or missing user authority.

## Ledger Audit

Run the bundled read-only audit before and after scheduling a batch:

```bash
python3 scripts/audit_ledger.py /absolute/path/to/experiment-ledger.md
```

Use `--json` for machine-readable output and `--strict` to treat warnings as failure. Review warnings manually because Markdown ledgers may intentionally repeat an experiment in summary and detail tables.

Before declaring the paper ledger reporting-ready, also run `--require-wandb-names --strict`. This requires every active/completed run to expose an explicit `W&B name=...` identity in addition to its URL.

## Expected Deliverables

For a planning or scheduling request, return:

1. a concise plan-coverage and status matrix grounded in the ledger and W&B;
2. unresolved protocol or capacity conflicts;
3. the next queue assignment and dependency chain;
4. complete hostname-bound prompts/commands for remote Codex sessions;
5. the exact ledger updates made.

Remote prompts must include their executable commands and W&B startup acceptance criteria; a prose-only instruction or naked launcher command is incomplete.

For a paper-status request, also return the unresolved required experiments separately from optional extensions and confirm that the ledger can locate every existing paper-facing result without relying on conversation memory.

For a result-analysis request, lead with the evidence, distinguish observation from causal interpretation, and update the ledger/progress document before closing.
