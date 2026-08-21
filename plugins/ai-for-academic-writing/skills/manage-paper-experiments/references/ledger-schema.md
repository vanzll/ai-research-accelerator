# Experiment Ledger Schema

The ledger is the authoritative mapping from paper claims to executable attempts and reported results. Keep it in version control next to the paper plan when possible.

## Required Views

A paper ledger should expose three linked views:

1. **Plan coverage:** every `plan.md` item, its paper role, coverage state, decisive evidence, and remaining action.
2. **Attempt registry:** reproducible runtime identity for every formal/baseline attempt, including failures and retries.
3. **Evidence index:** all paper-facing formal and historical runs with direct W&B/source links, compact key numbers, evaluator status, interpretation, and caveat.

The same run may appear in multiple views, but duplicated rows must agree. Queue state alone is not a complete paper ledger.

Adding an experiment in planning or discussion immediately creates or updates a plan-coverage row and a not-started attempt row. Do not wait until a launcher exists. Removing or deferring it changes the row state; it does not erase the record.

## Required Fields

Each formal attempt should record:

| Field | Meaning |
|---|---|
| Paper experiment ID | Stable human-readable identity, independent of W&B's run ID |
| Attempt | Monotonic attempt number; never reuse an old attempt after a semantic or infrastructure relaunch |
| Priority / role | Main table, training curve, appendix, diagnostic, baseline, or invalidated |
| Method | Exact algorithm variant and material flags |
| Model / benchmark | Model checkpoint, dataset, reward, prompt split, and evaluator |
| Seed | Explicit even when only one seed is planned |
| Budget | W&B steps, rollout epochs, reward calls, or GPU-hours, with semantics defined |
| Evaluation grid | Exact pre-registered steps eligible for best selection |
| Checkpoint policy | Best/final save steps, retention count, pruning policy |
| Code identity | Repository, branch, full commit SHA, launcher/config |
| Runtime identity | Hostname, queue/tmux ID, reservation, ports, log path |
| W&B identity | Entity, project, exact display name, run ID, URL, state, group/tags, first-history handshake |
| Artifacts | Best/final checkpoint or artifact, success marker, evaluation outputs |
| Results | Curve summary, best eval/step, final eval/step, per-component results |
| Termination | Completed, active stop, collapse, infrastructure failure, invalid config, or cancellation |
| Notes | Deviations, caveats, failure diagnosis, and paper-use decision |

Every terminal attempt must include a one-line result synopsis suitable for fast paper lookup. Every running attempt must include its W&B display name and URL as soon as the startup handshake completes.

Use a full 40-character commit SHA in the detailed attempt record. Short SHAs are acceptable only in compact summary tables that link back to the detailed record.

## State Machine

Recommended states:

- `not-started`
- `reserved`
- `queued`
- `running`
- `evaluating`
- `complete-formal`
- `complete-baseline`
- `complete-historical`
- `complete-valid-collapse`
- `cancelled`
- `invalid-config`
- `failed-infrastructure`
- `failed-discarded`

Allowed normal transitions:

```text
not-started -> reserved -> queued -> running -> evaluating -> complete-formal
                                        |             |
                                        |             +-> failed-infrastructure
                                        +-> complete-valid-collapse
                                        +-> invalid-config
                                        +-> cancelled
```

An infrastructure retry creates a new attempt and links to the prior attempt. It does not erase the original failure.

## Completion Rules

`complete-formal` normally requires:

- frozen config and full code SHA;
- valid W&B run URL or an explicitly documented fail-open local history;
- declared training budget reached, or an approved active-stop rule triggered;
- all required evaluation points attempted;
- best evaluation selected only from the allowed grid;
- final evaluation recorded separately;
- best and final checkpoint/artifact retained when promised;
- success marker and log location recorded.

Smoke tests and diagnostics should not use `complete-formal`; classify them by role.

## Result Identity

Never let these collapse into one number:

- peak train reward;
- final train reward;
- tail train reward;
- best held-out evaluation;
- final held-out evaluation;
- evaluation from a post-hoc or different evaluator.

For a multi-reward experiment, store the aggregate and every training/evaluation component. Preserve evaluator versions and prompt splits.

Historical evidence rows should record, when available:

- train peak and step, final, tail mean, and post-peak drawdown;
- held-out eval best/final and their steps, or explicit `no held-out eval`;
- the exact paper claim or ablation supported;
- config/protocol mismatch that prevents headline use;
- source location such as W&B URL, Numbers row, progress note, or offline probe artifact.

## Uniqueness and Conflict Rules

- One paper experiment ID may have multiple attempts, but each attempt has one frozen contract.
- One W&B training run ID belongs to one training attempt. A separately identified derived evaluation, such as a pretrained step-0 baseline extracted from that run, may reference the same source run when the ledger marks it explicitly as derived rather than as another training attempt.
- One active reservation belongs to one attempt.
- A relaunch gets a new attempt and usually a new W&B run.
- Duplicate appearances in overview/detail tables are allowed only when they resolve to the same attempt and state.
- Never assign a finished W&B run to a later replacement experiment because the names look similar.

## Reconciliation Order

Whenever the user asks to update, inspect, summarize, or audit the ledger, query W&B directly before editing it. At minimum read run state, display name, config, summary, and the targeted history needed for claimed key numbers. Logs and remembered links do not replace this query.

When sources disagree, inspect them in this order:

1. frozen launcher/config and code SHA;
2. W&B run config and history;
3. local queue log and success marker;
4. checkpoint/evaluation artifact metadata;
5. ledger summary text.

Correct the ledger to match the evidence and record the correction.
