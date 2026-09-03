---
name: manage-paper-experiments
description: Manage formal ML paper experiments from planning through reproducible reporting, including experiment ledgers, W&B observability, remote Goal prompts, run reconciliation, checkpoints, curves, and result tables.
---

# Manage Paper Experiments

Keep experiments scientifically comparable and recoverable without turning
every run into a software release project.

## Maintain one experiment ledger

Use the repository's existing ledger or progress document. Record the question,
experiment ID, intended single-variable delta, exact commit and command, model
and reward identities, data, seed, budget, W&B run, checkpoints, status, key
results, failures, and remaining uncertainty. Preserve failed attempts rather
than overwriting their lineage.

For detailed schemas, read [ledger-schema.md](references/ledger-schema.md) only
when creating or repairing a ledger format. For reporting, read
[reporting-protocol.md](references/reporting-protocol.md).

## Plan metrics around the hypothesis

Before launching, identify only metrics that can distinguish the hypothesis.
Depending on the method, consider:

- train/eval aggregate and component rewards;
- advantage or covariance scale and component contributions;
- policy, value/reference, KL, ratio, clip, and entropy diagnostics;
- gradient norm, clipping, parameter/update scale, and nonfinite counts;
- per-timestep, branch, prompt-group, diversity, and validity statistics;
- rollout, reward, backward, optimizer, communication, memory, and wall time.

State what each critical metric diagnoses. Do not add telemetry merely because
another run recorded it.

## Freeze the scientific comparison

Bind the exact commit, launcher/config, seed, data and prompt protocol, model and
reward revisions, optimizer/batch/group semantics, evaluation schedule, W&B
identity, budget, and success condition. Matched sibling experiments should use
one shared operational runtime and differ only in their declared scientific
variable.

If one sibling discovers an operational repair, mark comparisons provisional
until that repair is shared by subsequent siblings. Do not attribute an
operationally confounded outcome to the treatment.

## Delegate without duplicating development

When the user asks for an experiment prompt, compose with `multinode-training`
for distributed launch requirements. Consume the exact commit and command
produced by the implementation workflow; do not rerun its feature review,
incident archaeology, release construction, or broad tests.

The prompt should be self-contained enough that the remote Goal Agent can:

1. verify it is on an authorized training allocation;
2. source the site environment in the final persistent shell;
3. materialize the exact clean commit;
4. execute the frozen command under durable process ownership;
5. validate the declared W&B/training milestone;
6. leave a healthy formal run running; and
7. record any real repair in the repository-root `踩坑记录/` index.

Do not require a new launch bundle, production certificate, or release receipt
unless the repository already uses that artifact as its executable interface.
A naked command is acceptable only when it already encapsulates environment,
GPU lifecycle, logs, failure propagation, and acceptance; otherwise include the
minimal missing wrapper information in the prompt.

Prefer one master Goal Agent and deterministic workers. Use worker Agents,
shared-file buses, or relays only when the selected launcher cannot execute the
worker actions or independent Agent judgment is genuinely needed. Never keep an
Agent sleeping and polling when a deterministic supervisor can own the wait.

## Preserve cross-agent evidence

The remote record is the reply from the execution Agent to the coding Agent. It
should identify the supplied and successful commits/commands, observed failure
stage, primary evidence, relevant diff, validation, science impact, and
uncertainty. Before a later related prompt, read only new records since the
watermark and use `continuous-skill-learning` to verify and absorb applicable
repairs. Do not treat remote prose alone as causality proof.

## Monitor and reconcile

For a W&B run, inspect config, summary, and history rather than reward alone.
Check the declared horizontal axis, component metrics, optimization scale,
nonfinite signals, timing, memory, and whether tracker progress agrees with
rank/log evidence. Distinguish a stalled tracker from a stalled trainer.

Update the ledger with the exact W&B URL/name, latest meaningful step, runtime
commit, status, anomaly, checkpoint, and interpretation. Label infrastructure
failures, invalid configurations, and scientifically valid outcomes separately.

## Completion and reporting

Use the run's declared completion contract. A formal delegated training launch
is normally considered healthy only after at least five finite optimizer
updates and later-cycle progress while the process remains running; this is not
the same as full experiment completion.

Retain the checkpoint and metric history needed for paper curves. Keep raw
values and plotting data auditable, report uncertainty where seeds exist, and
do not silently mix incompatible metric definitions or x-axes.
