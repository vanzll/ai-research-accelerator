---
name: multinode-training
description: Design, implement, launch, audit, and debug reliable multi-node GPU training. Use for torchrun, Accelerate, DeepSpeed, DDP, FSDP, tensor or sequence parallel jobs; distributed RL pipelines with rollout or reward services; cluster launchers, topology changes, collective hangs, asset staging, checkpointing, and send-and-forget experiment queues.
---

# Multinode Training

Treat multi-node training as a distributed system with three separate contracts:

1. the computation contract: parallel dimensions, batch semantics, collectives, and optimizer equivalence;
2. the control-plane contract: node identity, rendezvous, process ownership, barriers, failure propagation, and recovery;
3. the dependency contract: code, model assets, data, local services, logs, checkpoints, and external trackers.

A successful `torchrun` command is not proof that all three contracts are correct.

## Load only the needed references

- Read [topology-and-semantics.md](references/topology-and-semantics.md) before changing world size, parallelism, batching, gradient accumulation, sampling groups, or checkpoint code.
- Read [reliable-launch.md](references/reliable-launch.md) before writing a launcher, supervisor, remote-agent prompt, asset preparation flow, or recovery policy.
- Read [diagnostics.md](references/diagnostics.md) when a job hangs, one node diverges, throughput regresses, metrics disagree, or startup does not reach training.
- Read [source-notes.md](references/source-notes.md) when refreshing the skill or checking which rules come from PyTorch, Accelerate, DeepSpeed, Megatron-LM, Hugging Face Hub, or NCCL.

## Establish a frozen run contract

Before editing code or allocating GPUs, write down and mechanically validate:

- experiment ID, attempt, launch nonce, exact commit, repository cleanliness, and config hash;
- ordered host list, expected hostname per node, `nnodes`, `nproc_per_node`, node ranks, world size, master address, and port;
- every parallel dimension and the resulting data-parallel replica count;
- local microbatch, gradient accumulation, global batch, prompt/group layout, and optimizer-step semantics;
- model, dataset, tokenizer, reward model, and auxiliary-service asset roots plus immutable revisions or manifests;
- checkpoint/evaluation schedule, retention, W&B identity, and success criteria;
- owner and cleanup behavior for every process, port, temporary directory, and resource lease.

Fail closed when a required value is implicit, inconsistent, or node-specific without being declared. Do not silently choose a different batch size, model path, network interface, precision, or microbatch after launch.

## Use a staged launch

Advance through these stages in order, with bounded waits and durable evidence:

1. **Preflight:** verify host identity, code commit, environment, free ports, storage, GPU inventory, and absence of unowned conflicting processes.
2. **Prepare immutable assets:** one coordinator writes; workers wait and verify. Never let all ranks mutate a shared model cache.
3. **Start node-local dependencies:** each node starts only its own reward/data services with the training rendezvous environment removed, then proves both process liveness and application readiness.
4. **Cluster-ready barrier:** require a nonce-bound ready record from every expected node. A rank-0 heartbeat alone is insufficient.
5. **Transport probe:** before loading the formal model, run a bounded collective with the exact nodes, GPUs, interfaces, and NCCL environment; verify the intended transport and a plausible bandwidth/latency floor.
6. **Distributed launch:** start the same frozen command on every node with unique node rank and identical rendezvous values.
7. **First-work validation:** require all ranks to join, one complete global batch or rollout, one optimizer step, globally reduced metrics, and any declared tracker run while workers are still alive.
8. **Durable handoff:** once validated, a deterministic supervisor owns monitoring, cleanup, and authorized transitions. Do not keep an agent polling.

For exact marker contents, asset rules, process-group cleanup, and remote prompt requirements, follow [reliable-launch.md](references/reliable-launch.md).

## Non-negotiable correctness rules

- All ranks must execute distributed collectives in the same order. Never put a collective checkpoint, metric reduction, or barrier inside a global-rank-zero-only branch.
- Treat `LOCAL_RANK`, `RANK`, and `WORLD_SIZE` as runtime identities. Elastic restarts may change global ranks; do not use them as durable experiment lineage.
- Reduce paper-facing metrics over the intended global population. A rank-0 local reward or component score is not a global training metric.
- Preserve semantic groups such as K samples from one prompt on the same logical estimator boundary when the algorithm requires it. Do not assume a generic distributed sampler preserves group contiguity.
- Distinguish model-sharding ranks from independent data replicas when computing global batch and sample count.
- A checkpoint is complete only after every required rank finishes its collective portion and a final success manifest is written last.
- A process existing is not readiness. Check the actual port or API and require a fresh heartbeat tied to the current nonce.
- A node-local service must not inherit `RANK`, `WORLD_SIZE`, `LOCAL_RANK`, `MASTER_ADDR`, `MASTER_PORT`, or equivalent training rendezvous state unless it is deliberately part of that worker group. Sanitize these variables at the service process boundary, not globally.
- Do not preserve inherited NCCL transport variables through `${VAR:-default}` in a frozen launcher. Resolve the intended interface and transport explicitly from the target hosts, then verify them with a collective probe. High GPU utilization alone does not prove useful compute.
- Establish an owned worker process group through a child handshake or bounded polling. Never make cleanup correctness depend on one immediate PID/PGID observation after `setsid` or a background fork.
- On any node failure, terminate the whole worker group unless the framework's elastic recovery semantics were deliberately designed and tested.
- Preserve failed attempt evidence. Retry with a new attempt and nonce after repairing the cause; do not overwrite ambiguous lineage.
- Treat a missing manifest as "not yet verified," not "asset missing." Before any download, discover declared existing asset roots, validate compatible files against the pinned revision/index/checksums, and import or link them into the immutable layout. Download only files that are absent or invalid.
- Record both the logical parallel mesh and its physical placement. Full-world FSDP can turn a transport mistake into per-layer cross-node stalls; compare it with node-local sharding plus cross-node replication only after transport correctness is established.
- Do not trade throughput for serialized algorithm equivalence unless the user explicitly asks to reproduce a larger logical batch or topology with fewer resources. Otherwise preserve the fastest correct parallel execution supported by the frozen protocol.

## Asset preparation contract

On shared storage, a coordinator process on the master host should run before the trainer process group exists. It should:

1. acquire a single-writer lock;
2. inspect declared existing model roots and compatible caches before downloading;
3. verify any existing candidate against the pinned revision, index, required files, sizes, and checksums;
4. import, hard-link, or symlink a verified candidate into the canonical immutable layout when safe;
5. download only missing or invalid files into an attempt-scoped temporary directory;
6. atomically publish the immutable asset directory or manifest;
7. write a nonce-bound ready record last.

Workers must only wait, then independently verify the published files. During training, use explicit local paths and offline or `local_files_only` loading. The presence of Hugging Face `blobs/` does not prove a usable `snapshots/` tree.

If storage is not shared, stage the same verified manifest to every node before the cluster-ready barrier. Do not pretend a rank-0 download is visible remotely.

## Low-resource equivalence is opt-in

When the user explicitly requests algorithm-equivalent execution with fewer GPUs, a larger parallel logical batch may be serialized into rollout or microbatch waves while the policy and optimizer boundary remain frozen. State the equivalence target, additional wall time, and residual numerical differences before implementing it. Follow the exact invariants in [topology-and-semantics.md](references/topology-and-semantics.md).

Do not enable this mode merely because GPUs are scarce. Without explicit user authorization, do not silently replace parallel execution with a slower serialized schedule.

## Validation ladder

Use the smallest test that can expose the next class of failure:

1. dependency-free config and launcher tests;
2. one process on CPU or one GPU;
3. one node with the final local process topology;
4. two nodes with one small collective and node-local services;
5. the exact full topology for one complete batch or rollout and checkpoint;
6. the formal run.

The smoke must preserve the formal topology and algorithm semantics. Reduce duration or data volume, not the number or ordering of distributed roles, unless that dimension is explicitly what the smoke is testing.

## Operate and diagnose from primary evidence

Record rank-prefixed logs, per-node supervisor state, ready/failed/success records, process groups, service ports, resource use, collective phase, globally reduced metrics, checkpoint manifests, and W&B run IDs. Classify a stall by its last completed stage before changing NCCL or training hyperparameters.

For research experiments, compose with `manage-paper-experiments` for paper IDs, ledger state, W&B reconciliation, and result reporting. Compose with `long-task-relay` only when a deterministic supervisor cannot decide the next action and human or agent judgment is genuinely required.

## Improve this skill from failures

When a real run exposes a reusable failure mode, first repair and document the immediate attempt. Then convert the lesson into the smallest general invariant, update the relevant reference, add a deterministic check when the property is mechanically testable, validate the plugin, and synchronize the local installed skill and repository source. Do not encode one cluster's aliases, paths, or scheduler as universal requirements.
