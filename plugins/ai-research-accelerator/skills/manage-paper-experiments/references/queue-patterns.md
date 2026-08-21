# GPU Queue and Waiter Patterns

Use these patterns to generate remote Codex prompts. Adapt paths and commands to the applicable `AGENTS.md`; never assume aliases or hostnames across projects.

## Choose the orchestration primitive

- Use a deterministic shell supervisor for a frozen formal queue. It may wait,
  launch, verify markers, and retry only pre-authorized infrastructure
  failures.
- Use an event-driven relay watcher when the next action requires interpreting
  W&B or applying a promotion rule. The watcher performs local observation only
  and wakes the exact Codex conversation once per persisted event.
- Never keep Codex alive to perform periodic status checks. Mechanical polling
  must not invoke a model.

## Remote Prompt Contract

Every prompt sent to a training-node Codex should include:

1. **Node identity:** exact expected `hostname -f`; fail closed if it differs.
2. **Scope:** what is already running, what must not be touched, and which queue this prompt owns.
3. **Code identity:** repository, branch, full commit SHA, launcher/config, and clean checkout path.
4. **Dependencies:** process, reservation, success-marker, and checkpoint conditions that gate the next run.
5. **Validation:** targeted tests, compile/syntax checks, disk check, ports, and duplicate-run check.
6. **Runtime:** tmux names, logs, W&B experiment IDs, evaluation/checkpoint protocol, and capacity policy.
7. **GPU ownership:** where `gpu_free` occurs and which outer process alone restores `gpu_hold`.
8. **Verification:** expected W&B display name, experiment ID, first config/history checks, and ledger facts to report back.
9. **Recovery loop:** exact commands and decision boundaries for pre-W&B failures, stale reservations, lost tmux after reboot, occupied nodes, and attempt-number escalation.
10. **Child-shell environment:** activation and executable/import probes performed inside the exact tmux or persistent shell that will launch training.
11. **Retry authority:** a bounded sequence of pre-authorized attempt and queue IDs so recoverable failures do not require another user message.

The prompt must be self-contained; assume the remote Codex has no prior conversation. Include complete checkout, test, and launch commands rather than referring to an earlier prompt.

## Send-and-Forget Startup Contract

The user should be able to send one prompt and stop supervising startup. The
remote Coding Agent owns only a bounded bootstrap window; a persistent
tmux/shell supervisor owns all subsequent waiting and stage transitions without
consuming model tokens.

For every experiment, require the supervisor to establish:

```text
W&B run exists
display name or deterministic name pattern matches
paper experiment ID and attempt match
full code SHA, seed, method, model, benchmark, budget, and eval grid match
first non-empty history row exists
run URL, run ID, display name, host, queue, and log are reported for ledger ingestion
```

For a stage that launches immediately, the agent polls W&B only until the first
valid history row. For stages scheduled hours later, the deterministic
supervisor performs this handshake and writes an atomic startup marker; the
agent validates that logic and exits. Local stdout, a PID, GPU utilization,
tmux, or a reservation alone is never a run-start acceptance criterion.

Before the handshake:

- repair transient checkout, environment, port, W&B init, and launcher failures and retry;
- source the environment bootstrap and activate Conda inside the final tmux shell, then record `command -v python`, `command -v accelerate`, the active environment, required import probes, and the `__file__` provenance of repository-local packages before `gpu_free`;
- prepend the frozen checkout to `PYTHONPATH` when the training entrypoint can otherwise resolve an editable install, and reject any repository package whose resolved path is outside that checkout;
- if the node is occupied, create a persistent waiter with a durable
  shared-storage heartbeat, verify its exact dependency and launch command, and
  exit instead of polling until the node becomes free;
- after a reboot, reconcile shared logs/reservations/markers and W&B before deciding whether the same attempt never started or a new attempt is required;
- treat a launcher invocation as pre-start when no W&B run exists and logs prove failure before model/optimizer execution; preserve its diagnostics and continue automatically;
- reuse an attempt ID only when no externally visible reservation/name was exposed and there is positive evidence that no W&B run was created and no optimizer update could have occurred; otherwise advance to the next pre-authorized attempt even for a pre-start failure;
- once a run exists or training may have begun, preserve the failed attempt and allocate the next attempt ID.

The remote prompt must pre-authorize a bounded retry ladder, normally three attempt IDs. For each failed launch it must classify the boundary, retain logs, repair the infrastructure cause, advance lineage when required, and retry. It may not stop after merely diagnosing a missing package, wrong PATH, dead tmux, occupied port, transient checkout failure, or missing W&B initialization.

Do not let W&B fail-open silently satisfy formal startup. Fail-open is allowed only after a valid run identity and local-to-W&B reconciliation path have been established. A formal queue should write an atomic startup marker containing display name, run ID, URL, experiment ID, SHA, and first-history step.

For a sequential queue, the supervisor must validate every later stage, write
atomic startup/completion/failure markers, and maintain a timestamped heartbeat.
The remote agent validates these code paths and returns after the immediate
stage handshake or waiting-supervisor bootstrap. It must never consume tokens
by monitoring later stages for hours. If the supervisor exhausts its recovery
ladder, it writes a durable blocker marker for the next reconciliation session.

## Attempt Boundary

Use this order to classify a failed launch:

1. Query W&B for the exact experiment ID and display-name pattern.
2. Inspect logs for model construction, backward/optimizer steps, and local W&B identity.
3. If no W&B identity exists and optimizer execution is ruled out, classify it as pre-start infrastructure. Preserve the log, repair, and continue.
4. If W&B exists or optimizer execution cannot be ruled out, retain the attempt as a real failed attempt and continue with the next attempt ID.

Never use “the shell script started” or “the package imported successfully” as the attempt boundary. Verify that the package imported from the intended frozen checkout.

## Immediate Sequential Queue

Conceptual outer wrapper:

```bash
source /shared/path/my_bashrc.sh
gpu_free
trap 'gpu_hold' EXIT

run_and_verify EXPERIMENT_A
run_and_verify EXPERIMENT_B
```

`run_and_verify` must write separate logs/reservations, propagate nonzero exit status, validate the expected success marker, and stop the queue on a failed dependency unless the plan explicitly says otherwise.

## Persistent Waiter

Use a waiter when current work must finish before a replacement queue can start:

```text
loop:
  inspect owned queue/processes and dependency markers
  if another owned experiment is active: sleep with bounded polling
  elif required success marker is absent: fail closed
  else: create and verify the next persistent queue, then exit
```

The waiter should be a tmux session with a durable log. It must not reserve or release GPUs while merely waiting.

Process absence alone is insufficient. A prior experiment may have crashed without producing its success marker.

## Concurrent Jobs on One Node

When capacity allows two jobs:

- use one outer queue as the GPU lifecycle owner;
- start both child jobs with disjoint ports, tmux/session IDs, logs, reservations, W&B identities, and output directories;
- wait for both process groups;
- verify both completion contracts;
- call `gpu_hold` only after both have exited.

Do not put `trap 'gpu_hold' EXIT` independently in each child; the first completed child could reclaim GPUs from the sibling.

## Safe Checkout

Prefer a node-specific clean worktree or clone at the exact SHA. Before launch verify:

```text
hostname matches
HEAD equals full SHA
tracked worktree is clean
launcher/config exist
required tests pass
disk headroom is sufficient
no duplicate experiment or reservation is active
```

Untracked logs or outputs should live outside the checkout when possible. Never reset or clean a shared working tree destructively.

## Success Markers

A marker should include or point to:

- paper experiment ID and attempt;
- exact SHA and config;
- W&B run ID;
- exit status and final step;
- best/final evaluation status;
- best/final checkpoint paths;
- completion timestamp.

Write it atomically only after the declared completion contract succeeds. Failure markers should be distinct and retained.

Use a separate startup marker for the W&B handshake. Never use queue reservation or process creation as a substitute for either startup or completion markers.

## W&B Fail-Open Boundary

W&B upload failures may fail open so training continues, but reproducibility still requires durable local logs and a later reconciliation path. Fail-open must not hide:

- config mismatch;
- evaluator failure;
- missing checkpoint;
- non-finite training;
- disk exhaustion affecting non-W&B outputs.

Report a run as locally complete but W&B-incomplete until reconciliation finishes.
