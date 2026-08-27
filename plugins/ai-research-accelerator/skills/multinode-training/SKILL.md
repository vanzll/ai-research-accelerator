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

Solve the topology arithmetic before choosing a node count. Check that every
parallel degree divides the relevant world/model dimensions, semantic groups
divide the true DP population, and the proposed microbatch fits after the
actual SP/TP split. More GPUs do not repair an invalid mesh.

## Use proportionate launch assurance

The stages below describe separate failure domains, not mandatory work for every launch. Run only the smallest set not already covered by fresh, matching evidence:

1. **Preflight:** verify host identity, code commit, environment, free ports, storage, GPU inventory, and absence of unowned conflicting processes.
2. **Prepare immutable assets:** one coordinator writes; workers wait and verify. Never let all ranks mutate a shared model cache.
3. **Start node-local dependencies:** each node starts only its own reward/data services with the training rendezvous environment removed, then proves both process liveness and application readiness.
4. **Cluster-ready barrier:** require nonce- and child-identity-bound application readiness from every expected node. A rank-0 process alone is insufficient.
5. **Transport validation:** if the hosts, topology, network stack, or loaded communication library are new or changed, run a bounded collective with the exact topology. Otherwise verify and reuse a frozen report from repeated successful probes with matching identities.
6. **Distributed launch:** start the same frozen command on every node with unique node rank and identical rendezvous values.
7. **First-work validation:** persist immutable local evidence when all ranks complete one global batch or rollout and optimizer step; verify finite global metrics and tracker visibility independently.
8. **Durable handoff:** once validated, a deterministic supervisor owns monitoring, cleanup, and authorized transitions. Do not keep an agent polling.

Do not insert a new smoke between an already successful exact-topology smoke and a formal run unless code, assets, topology, communication stack, or algorithm semantics changed. A direct formal launch with an early first-work handshake is appropriate when matching evidence already exists. For exact marker contents, evidence reuse, asset rules, process-group cleanup, and remote prompt requirements, follow [reliable-launch.md](references/reliable-launch.md).

Keep a strict complexity budget: prefer one canonical contract validator, one
node wrapper, and one deterministic supervisor. A new gate is justified only
when it catches a distinct expensive failure before that failure can occur.
Do not duplicate parsers, nest smoke-to-formal promotion controllers, or add a
watcher merely to re-prove evidence already frozen elsewhere.

## AI-assisted repair and node collaboration

Load `shared-filesystem-agent-coordination` before designing remote-Agent
prompts, a shared-file message bus, or an autonomous repair loop. It owns the
general coordinator/worker topology, first-mile bootstrap, request/ACK/result
protocol, exact-thread relays, monitoring, and closure rules.

For training, freeze a machine-readable scientific contract before granting
repair authority. It must cover the algorithm/objective, model and reward
identities, data and prompt protocol, batch/group and optimizer semantics,
precision, sampling, parallel mesh, evaluation, and checkpoints. Operational
repairs to communication, launching, environment activation, process ownership,
telemetry, or framework compatibility are allowed only when that hash and the
runtime semantic quantities remain unchanged. Shared repairs require a
regression test, new commit, and new attempt/nonce; uncertain changes require
user approval.

The Node 0 Goal may own global diagnosis and semantics-preserving recovery only
through the declared first-work gate. Deterministic supervisors own waiting and
training processes; ordinary worker Agents handle bounded node-local incidents.
Worker dispatchers remain alive across failed training attempts and terminate
normally only after validating the Node 0 coordinator's fenced
`GOAL_COMPLETED` directive; attempt evidence and trainer processes remain
attempt-scoped. Failure or idle states do not authorize dispatcher shutdown.
`AGENT_BUS_READY` proves only Agent coordination. Require independent
`NODE_LOCAL_READY`, `CLUSTER_READY`, `TRAINING_STARTED`, and
`FIRST_WORK_VALIDATED` evidence before claiming distributed training success.

## Non-negotiable correctness rules

- All ranks must execute distributed collectives in the same order. Never put a collective checkpoint, metric reduction, or barrier inside a global-rank-zero-only branch.
- Treat `LOCAL_RANK`, `RANK`, and `WORLD_SIZE` as runtime identities. Elastic restarts may change global ranks; do not use them as durable experiment lineage.
- Reduce paper-facing metrics over the intended global population. A rank-0 local reward or component score is not a global training metric.
- Preserve semantic groups such as K samples from one prompt on the same logical estimator boundary when the algorithm requires it. Do not assume a generic distributed sampler preserves group contiguity.
- Distinguish model-sharding ranks from independent data replicas when computing global batch and sample count.
- A checkpoint is complete only after every required rank finishes its collective portion and a final success manifest is written last.
- A process existing is not readiness. Require a nonce- and child-identity-bound application check; use a heartbeat only when no reliable health endpoint exists.
- A node-local service must not inherit `RANK`, `WORLD_SIZE`, `LOCAL_RANK`, `MASTER_ADDR`, `MASTER_PORT`, or equivalent training rendezvous state unless it is deliberately part of that worker group. Sanitize these variables at the service process boundary, not globally.
- Do not preserve undeclared inherited NCCL transport variables through `${VAR:-default}` in a frozen launcher. Resolve the complete platform-approved transport contract explicitly, then verify it with a fresh probe or a matching frozen report. High GPU utilization alone does not prove useful compute.
- Treat the loaded communication binary as part of the contract. Two libraries may report the same NCCL ABI/version while selecting radically different vendor transports. On clusters with a site NCCL/KCCL build, verify the resolved `libnccl.so` path, preload the pinned vendor library when required, and record its checksum; HCA/QP/GID tuning cannot repair the wrong implementation.
- Treat interface, HCA, GID, and NUMA selectors as allocation-local facts. Before rendering a launcher, collect the actual GPU/fabric topology on every host and mechanically verify every selected device exists, is active, and maps to the intended network path. A validated communication-library path may be reusable; HCA names from another host or allocation are not. Never make all workers satisfy the coordinator's device names merely because the machines appear similar.
- Prefer a one-shot adaptive fabric preflight for reusable launchers on new allocations: every node discovers its local topology, one coordinator atomically freezes an allocation contract, every worker validates its own contract slice, and a short exact-world collective verifies the selected transport before the same invocation directly enters formal training. Keep manual topology probes as a diagnostic fallback, not a routine user prerequisite. Select communication libraries only from an explicit platform allowlist; discovery must never preload an arbitrary library merely because it exists.
- Freeze the discovered communication library path and checksum, socket interface, port-qualified HCA list, GID, probe parameters, and host order. Source that same per-node contract into the formal trainer and test that no legacy rank policy rewrites it after the probe; a fast preflight is meaningless if formal training silently uses different rails or a different NCCL binary.
- Activate and verify the exact Python/launcher/import paths inside the final
  persistent child shell. A parent-shell import or Conda activation does not
  prove that tmux, a scheduler, or a later relay inherited the same environment.
- Establish an owned worker process group through a child handshake or bounded polling. Never make cleanup correctness depend on one immediate PID/PGID observation after `setsid` or a background fork.
- On any node failure, terminate the whole worker group unless the framework's elastic recovery semantics were deliberately designed and tested.
- Preserve failed attempt evidence. Retry with a new attempt and nonce after repairing the cause; do not overwrite ambiguous lineage.
- Implement experiment-ID parsing, contract validation, and identity derivation once and test multi-digit attempts. Duplicated outer/inner validators create contradictory control planes.
- Treat a missing manifest as "not yet verified," not "asset missing." Before any download, discover declared existing asset roots, validate compatible files against the pinned revision/index/checksums, and import or link them into the immutable layout. Download only files that are absent or invalid.
- Record both the logical parallel mesh and its physical placement. Full-world FSDP can turn a transport mistake into per-layer cross-node stalls; compare it with node-local sharding plus cross-node replication only after transport correctness is established.
- Do not trade throughput for serialized algorithm equivalence unless the user explicitly asks to reproduce a larger logical batch or topology with fewer resources. Otherwise preserve the fastest correct parallel execution supported by the frozen protocol.
- Persist rank-prefixed runtime output from the first process launch. Use tensor collectives for transport measurements and structured per-rank records for diagnostics; do not use Python object collectives or interleaved multi-rank stdout as a bandwidth oracle.
- Decouple tracker startup from expensive evaluation. Immediately after tracker initialization, log a lightweight identity/telemetry row and persist its local commit evidence before starting step-zero evaluation. An evaluation-duration timeout or delayed cloud history must not be interpreted as training failure.

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

## Validation ladder and evidence reuse

Use the smallest test that can expose the next class of failure:

1. dependency-free config and launcher tests;
2. one process on CPU or one GPU;
3. one node with the final local process topology;
4. two nodes with one small collective and node-local services;
5. the exact full topology for one complete batch or rollout and checkpoint;
6. the formal run.

This is a diagnostic ladder, not a requirement to rerun every rung for every attempt. Record evidence identities so a later launch can reuse results only when hosts, topology, communication binary/environment, code path, and relevant assets still match.

When a smoke is needed, it must preserve the formal topology and algorithm semantics. Reduce duration or data volume, not the number or ordering of distributed roles, unless that dimension is explicitly what the smoke is testing. After such a smoke passes, launch formal training directly; do not add promotion machinery whose only purpose is to re-prove the same facts.

## Operate and diagnose from primary evidence

Record rank-prefixed logs, per-node supervisor state, ready/failed/success records, process groups, service ports, resource use, collective phase, globally reduced metrics, checkpoint manifests, and W&B run IDs. Milestone evidence must be append-only or step-specific: a later rank exit must not overwrite proof that all ranks completed an earlier step. Classify a stall by its last completed stage before changing NCCL or training hyperparameters.

For research experiments, compose with `manage-paper-experiments` for paper IDs, ledger state, W&B reconciliation, and result reporting. Compose with `long-task-relay` only when a deterministic supervisor cannot decide the next action and human or agent judgment is genuinely required.

Select one agent-control mode per conversation and unresolved objective. If the
user explicitly chooses Goal mode, do not add a relay for that same objective.
Different nodes may use different modes under an explicit coordinator-worker
protocol. For long waits, prefer a token-free supervisor or event-driven relay;
use agents only for actionable diagnosis and bounded repair.

## Improve this skill from failures

When a real run exposes a reusable failure mode, first repair and document the immediate attempt. Then convert the lesson into the smallest general invariant, update the relevant reference, add a deterministic check when the property is mechanically testable, validate the plugin, and synchronize the local installed skill and repository source. Do not encode one cluster's aliases, paths, or scheduler as universal requirements.
