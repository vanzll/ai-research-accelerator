---
name: multinode-training
description: Design, launch, and debug reliable multi-node GPU training, including distributed RL, torchrun, MPI, DDP/FSDP, model parallelism, remote Goal prompts, and recovery from collective or lifecycle failures.
---

# Multinode Training

Treat a distributed run as three contracts:

1. computation: parallel dimensions, batch/group semantics, collectives, and
   optimizer equivalence;
2. control plane: rank identity, rendezvous, process ownership, failure
   propagation, and cleanup;
3. dependencies: exact code, assets, environment, logs, checkpoints, and
   trackers.

This skill preserves non-obvious distributed invariants and Agent handoffs. It
does not prescribe ordinary single-Agent coding technique.

## Load details only when needed

- Read [topology-and-semantics.md](references/topology-and-semantics.md) when
  changing world size, DP/FSDP/HSDP/SP/TP, batch, accumulation, or sample groups.
- Read [reliable-launch.md](references/reliable-launch.md) when creating or
  repairing a launcher, supervisor, environment boundary, GPU lease, or remote
  Goal prompt.
- Read [production-runtime-promotion.md](references/production-runtime-promotion.md)
  only when a real remote incident produced a code repair that must be promoted.
- Read [diagnostics.md](references/diagnostics.md) only when diagnosing a hang,
  crash, throughput regression, or metric disagreement.

## Route for speed

Choose the smallest route that matches the change.

### Routine experiment or parameter/profile change

Reuse the latest successful launcher and runtime when their relevant inputs are
unchanged. Freeze the intended scientific delta, run focused config/launcher
checks, commit and push the exact code, then emit the launch command or remote
prompt. Do not recreate production certificates, asset inventories, transport
probes, launch bundles, or broad regressions merely because a new experiment ID
or parameter changed.

### New algorithm, backend, or shared distributed path

Freeze a concise semantic contract and test the affected behavior and existing
callers. Compose with `contract-driven-feature-development`. Independent review
is optional by default and limited to one reviewer when the user requests it,
the new algorithm can silently violate its reference semantics, or a real
runtime incident required shared-core repair.

### Real runtime incident

Preserve the failed attempt, identify its last completed distributed stage, and
repair the smallest cause without changing the scientific contract. Compare the
prompt commit with the successful runtime commit and promote verified reusable
repairs before the next related launch. Use
`production-runtime-promotion.md` only for this route or when the repository
already has an explicit production-promotion mechanism.

Release artifacts such as manifests, receipts, and bundle hashes are required
only when the repository already treats them as its launch interface or the user
asks for them. Do not invent a release system for a routine research run.

## Freeze only the relevant contract

Before changing science, record the fields whose meaning can change: algorithm
and reward objective, model/data identities, sampling, batch/group and optimizer
semantics, parallel mesh, evaluation, and checkpoints. Before launch, also bind
the exact commit, attempt/nonce, host/rank mapping, environment, rendezvous,
asset roots, tracker identity, process ownership, and success condition.

Fail closed on an undeclared scientific change. Operational repairs to launch,
communication, environment, telemetry, and process lifecycle are allowed only
while the frozen scientific values remain unchanged; uncertain changes require
user approval and a new experiment identity.

## Prefer one master and deterministic workers

Use an allocation-native launcher such as MPI or Slurm when the platform
provides it. Otherwise use authenticated coordinator-to-worker execution such
as SSH. Prefer one master/Node 0 Goal Agent plus deterministic node wrappers;
worker Coding Agents are unnecessary when the coordinator can execute the
frozen command remotely.

Use `shared-filesystem-agent-coordination` only when workers need independent
Agent judgment or no direct executor exists. Do not add an Agent bus to a
working scheduler or SSH launch path.

## Preserve the local-to-remote Agent loop

The local coding Agent should hand off an exact reachable commit and a
secret-free, directly executable launch command. The remote Goal Agent should
primarily execute, observe, and keep the formal run alive. It may repair
semantics-preserving operational failures, but it must not silently change the
algorithm, reward, data, batch, optimizer, or evaluation contract.

Use the repository-root `踩坑记录/` index as their asynchronous communication
medium. A remote repair record identifies the supplied commit/command, failed
stage and evidence, successful commit/command, relevant Git delta, tests,
science impact, and uncertainty. Before generating the next related prompt, the
local Agent reads only records newer than its watermark, verifies material
claims, and absorbs applicable code repairs. Compose with
`continuous-skill-learning`; do not rely on either Agent remembering chat
history.

## Keep essential distributed invariants

- All ranks execute collectives in the same order. Rank-zero-only branches must
  not contain collectives required by other ranks.
- Compute global batch and semantic groups from the actual DP replicas after
  SP/TP/FSDP placement. Preserve prompt groups on the estimator boundary.
- Treat process existence as insufficient readiness. Bind evidence to the
  attempt, child identity, rank/host, and expected application milestone.
- Source and verify the site environment inside every final child shell that
  downloads assets or starts services, probes, evaluators, or trainers. Do not
  print or persist credentials.
- One coordinator prepares shared assets; workers verify them. A missing
  manifest means unverified, not necessarily missing, and should not trigger an
  unconditional redownload.
- Treat the loaded NCCL/KCCL or site communication library, interface, and
  topology as runtime facts. Reuse matching successful evidence; probe only
  when hosts, topology, library, or critical collectives changed.
- Keep Python object metadata off NCCL-capable groups when it can stage material
  GPU allocations; use tensor collectives for numeric payloads and a dedicated
  Gloo group for object metadata when needed.
- Own complete process groups and propagate failure to the whole attempt unless
  elastic recovery was deliberately implemented.
- Treat idle GPU reservation as a generation-fenced lease. An old attempt's
  cleanup must not restore the hold while a successor owns the GPUs.
- Keep science, logs, checkpoints, and failure lineage; clean only identity-
  verified stale runtime processes and ephemeral state.

## Launch and accept proportionately

Use existing matching evidence whenever possible. A routine launch normally
needs only current host/capacity checks, exact checkout/environment validation,
and the formal command. Run an exact-topology transport smoke only when relevant
transport inputs changed or no matching evidence exists.

Persist rank-prefixed logs and enough phase evidence to distinguish launcher,
collective, rollout, reward, backward, optimizer, tracker, and cleanup failures.
For a delegated formal run, do not declare normal operation from the first W&B
row or first update. Require at least five finite global optimizer updates and
evidence that a later cycle is advancing, then leave the trainer, durable
supervisor, tracker, and GPU lease running unless the user explicitly requested
a bounded smoke.

Do not make a remote Goal prompt substitute for unfinished local implementation.
Finish the launcher as far as the available environment permits; remote repair
authority is a fallback for real environment failures, not the planned coding
loop.
