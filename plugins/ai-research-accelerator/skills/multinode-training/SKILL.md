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
- placement and estimated phase-specific memory budget for applicable
  reward/evaluation services, model decoding, rollout, backward, optimizer, and
  checkpointing; refine it with measured representative peaks before increasing
  a configuration to the memory limit;
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

First-work validation is a handoff milestone, not permission to stop a formal
experiment. Unless the frozen contract explicitly defines a bounded smoke that
must stop after acceptance, successful delegation means
`FIRST_WORK_VALIDATED_AND_RUNNING`: record the evidence, leave the trainer,
tmux/supervisor, GPU lease, and tracker run alive, and hand monitoring to the
deterministic supervisor. Agent or Goal completion is separate from job
completion. A remote Agent must not send an interrupt, close the session,
restore the idle GPU reservation, or finish/crash the tracker merely because
the first-work gate passed.

Do not insert a new smoke between an already successful exact-topology smoke and a formal run unless code, assets, topology, communication stack, or algorithm semantics changed. A direct formal launch with an early first-work handshake is appropriate when matching evidence already exists. For exact marker contents, evidence reuse, asset rules, process-group cleanup, and remote prompt requirements, follow [reliable-launch.md](references/reliable-launch.md).

Keep a strict complexity budget: prefer one canonical contract validator, one
node wrapper, and one deterministic supervisor. A new gate is justified only
when it catches a distinct expensive failure before that failure can occur.
Do not duplicate parsers, nest smoke-to-formal promotion controllers, or add a
watcher merely to re-prove evidence already frozen elsewhere.

Commit recurring preflight and consolidation logic as deterministic scripts
with versioned result schemas. Remote Agents execute and interpret those
scripts; they do not each improvise a parser for the same evidence. Keep
immutable science fields separate from dynamic attempt/fencing state so a valid
retry is not rejected by a stale hard-coded validator.

Treat one-shot launcher readiness as the implementation Agent's responsibility,
not as work to defer to the training-node Coding Agent. Before handing off a
launch command or Goal prompt, finish and freeze the node wrapper, allocation
adapter, environment inheritance, rank mapping, process ownership, failure
propagation, GPU lease, evidence paths, and relevant regression tests; replay
fresh matching evidence for any expensive property that cannot be tested
locally. Remote semantics-preserving repair authority is an emergency safety
net, not the planned development or integration loop.

## Keep cluster launch backends replaceable

Separate the backend-neutral node runner from allocation launch adapters. The
node runner consumes an explicit node rank, node count, local GPU count, master
address/port, and frozen training command. Thin adapters translate platform
state into that contract, for example MPI, Slurm, direct SSH, or a Kubernetes
operator. Do not put hostfiles, scheduler variables, site paths, or hard-coded
hosts into the scientific launcher.

Prefer an allocation-native launcher after a bounded no-GPU allocation probe
proves the expected hosts, slots, rank mapping, and remote execution. On an MPI
allocation, start one foreground wrapper per node and let each wrapper start the
existing local `torchrun`; use no CPU binding unless a validated policy is
explicitly configured. Keep hostfiles optional because scheduler-integrated MPI
may already know the allocation. Do not make direct `mpirun -np <world> python`
the default until rank/environment/signal behavior has separate evidence.

Select the backend explicitly; do not guess from whichever executable happens
to be installed. Priority is: verified allocation-native launcher, authenticated
coordinator-to-worker execution, then an Agent bus. When the user requests a
remote launch prompt, provide one self-contained master/Node 0 Goal prompt that
runs the frozen adapter and continues through first-work validation. State the
postcondition explicitly: after validation, formal training remains running
under its durable supervisor unless the user requested a bounded smoke. Worker
Agents are unnecessary for deterministic node wrappers.

## AI-assisted repair and node collaboration

Before introducing an Agent bus, run a bounded authenticated remote-execution
probe from the coordinator to every worker. If the coordinator can execute the
frozen node-local commands through SSH, a scheduler, or another approved remote
executor, prefer one coordinator plus deterministic worker supervisors. Use a
multi-Agent bus only when workers need independent Agent judgment or no direct
executor is available.

For a fixed allocation with direct execution, give only Node 0 a Goal prompt.
Freeze `node rank -> connection endpoint -> expected hostname`, have Node 0
connect through the working endpoint and attest the returned hostname before
each launch, and start the frozen node wrapper in a durable node-local
supervisor. Worker nodes do not need Coding Agents. Use shared storage for
contracts, logs, milestones, and terminal evidence, not as a message bus.

Load `shared-filesystem-agent-coordination` before designing remote-Agent
prompts, a shared-file message bus, or an autonomous repair loop. It owns the
general coordinator/worker topology, first-mile bootstrap, request/ACK/result
protocol, stateless worker execution, optional resume adapters, monitoring, and
closure rules.

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
training processes. When an Agent bus is actually required, ordinary worker
Agents handle bounded node-local incidents. Worker dispatchers remain alive
across failed training attempts and terminate
normally only after validating the exact Node 0 host and Goal thread's fenced
`GOAL_COMPLETED` directive; attempt evidence and trainer processes remain
attempt-scoped. Failure or idle states do not authorize dispatcher shutdown.
Cluster readiness must bind each worker to the exact expected Agent campaign:
canonical campaign root/ID, science-contract hash, coordinator authority,
node/host, dispatcher process generation, and current attempt/nonce/fencing
epoch must all match. A healthy dispatcher from an older experiment or
campaign is unrelated and cannot satisfy readiness.
`AGENT_BUS_READY` proves only Agent coordination. Require independent
`NODE_LOCAL_READY`, `CLUSTER_READY`, `TRAINING_STARTED`, and
`FIRST_WORK_VALIDATED` evidence before claiming distributed training success.

Before launching a new campaign's GPU workload, have every host perform
identity-scoped retirement cleanup for older campaigns: stop only verified old
trainer, reward-service, Agent, supervisor, and tmux process groups; restore
the node's idle GPU reservation policy; and remove only dead-owner ephemeral
locks, PID files, sockets, and incomplete temporary state. Preserve experiment
logs, markers, results, checkpoints, and immutable failure lineage. Broad
`pkill` patterns, cache deletion, and concurrent worker mutation of shared
evidence are forbidden. When the old Agent bus is needed to bootstrap its
successor, validate the successor first, then clean the old campaign before
starting the new trainer.

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
- A transport probe must exercise every performance-critical formal process-group shape with its actual collective class and representative tensor size. In particular, a default-world all-reduce does not validate an FSDP shard-group all-gather, an SP all-to-all, or multiple concurrently initialized communicators. Record per-rank completion and fail if even one expected rank is absent; do not accept aggregate throughput from a different group as proof that formal training can communicate.
- Validate the communication implementation actually mapped in every probe/trainer process, not merely an `LD_PRELOAD` or contract path. Compare `/proc/self/maps` (or the platform equivalent), path, checksum, plugin policy, and successful transport logs; reject Socket fallback, failed-RDMA messages, unexpected plugins, and environment claims that disagree with the loaded binary.
- Freeze the discovered communication library path and checksum, socket interface, port-qualified HCA list, GID, probe parameters, and host order. Source that same per-node contract into the formal trainer and test that no legacy rank policy rewrites it after the probe; a fast preflight is meaningless if formal training silently uses different rails or a different NCCL binary.
- Activate and verify the exact Python/launcher/import paths inside the final
  persistent child shell. A parent-shell import or Conda activation does not
  prove that tmux, a scheduler, or a later relay inherited the same environment.
- Treat the user/cluster environment bootstrap as part of the launch contract.
  Every independent child-shell boundary that prepares assets or starts a
  downloader, dispatcher, probe, reward service, evaluator, or trainer must
  source the declared bootstrap inside that final shell before doing work. This
  is where site proxy, Hugging Face authentication, Python/Conda paths, and
  communication-library settings may be established. Verify required variables
  by presence or non-secret fingerprints; never print their values, persist
  credentials in shared state, or rely on a parent Agent shell having sourced
  them. After sourcing, sanitize role-inappropriate variables at the child
  boundary as required above.
- When a child consumes a generated shell contract such as `runtime.env`, source it with explicit export semantics (`set -a` or an equivalent structured launcher API) and test inheritance in the final process. Shell variables visible to the wrapper are not automatically environment variables visible to `torchrun`. If the site bootstrap is not nounset-safe, source it before enabling `set -u`, then enable strict mode for the owned launcher.
- Establish an owned worker process group through a child handshake or bounded polling. Never make cleanup correctness depend on one immediate PID/PGID observation after `setsid` or a background fork.
- Treat node-level resource hooks such as idle GPU reservation as a fenced
  lease, not an attempt-local boolean. Acquisition publishes an owner and
  monotonically newer generation under a node-local lock. A cleanup trap may
  restore the idle state only if its owner/generation is still current and no
  successor workload lease is active; a stale attempt exiting after its
  successor must be a no-op. Keep the generation lock held until the idle-state
  restore itself completes, so a successor cannot run its release/acquire hook
  between ownership validation and the old attempt's delayed restore.
  Idempotency within one trap is insufficient.
- On any node failure, terminate the whole worker group unless the framework's elastic recovery semantics were deliberately designed and tested.
- Preserve failed attempt evidence. Retry with a new attempt and nonce after repairing the cause; do not overwrite ambiguous lineage.
- Before relying on frozen code on multiple nodes, prove reachability and
  identity through the launcher's actual staging path in every distinct worker
  credential/network domain. For Git staging, a successful local `git cat-file`
  is insufficient; for containers, bundles, shared worktrees, or copied trees,
  verify the corresponding immutable artifact and the wrapper's actual import
  path.
- Treat layered compatibility patches as executable build artifacts. Generate
  them from real pinned checkout states, apply the complete chain to a clean
  checkout, test the resulting behavior, and hash the final applied tree or
  diff. When that identity changes, update and test every launcher, preparer,
  and runtime guard that consumes it; validating only the patch producer is
  insufficient.
- Implement experiment-ID parsing, contract validation, and identity derivation once and test multi-digit attempts. Duplicated outer/inner validators create contradictory control planes.
- Treat a missing manifest as "not yet verified," not "asset missing." Before any download, discover declared existing asset roots, validate compatible files against the pinned revision/index/checksums, and import or link them into the immutable layout. Download only files that are absent or invalid.
- Record both the logical parallel mesh and its physical placement. Full-world FSDP can turn a transport mistake into per-layer cross-node stalls; compare it with node-local sharding plus cross-node replication only after transport correctness is established.
- When scaling a working single-node FSDP recipe, freeze the intended shard
  degree and locality explicitly. Leaving `replicate=1` unchanged while world
  size grows silently turns node-local shard groups into full-world groups;
  prefer an explicitly validated HSDP mesh when preserving node-local shards.
- Treat evaluation as distributed work. If independent DP replicas redundantly
  generate the same validation set, shard examples across DP groups while SP/TP
  peers keep identical inputs and every collective group executes equal padded
  wave counts; score and retain only the unique, ordered examples.
- Do not trade throughput for serialized algorithm equivalence unless the user explicitly asks to reproduce a larger logical batch or topology with fewer resources. Otherwise preserve the fastest correct parallel execution supported by the frozen protocol.
- Persist rank-prefixed runtime output from the first process launch. Use tensor collectives for transport measurements and structured per-rank records for diagnostics; do not use Python object collectives or interleaved multi-rank stdout as a bandwidth oracle.
- Keep Python object metadata off NCCL-capable process groups when its
  serialization or device staging can create material GPU allocations. Reuse a
  group only when its backend is explicitly dedicated Gloo; ambiguous,
  wrapper-reported, mixed, or NCCL-capable groups require a separately created
  and cached Gloo group with the exact same members. Use tensor collectives for
  large numeric payloads.
- Treat process enumeration as racy: a PID may exit between discovery and
  `/proc` inspection. `ESRCH` is an idempotent teardown no-op, but preserve any
  evidence of an unexpected prior exit and verify that the complete owned
  process group is empty; identity mismatches remain errors.
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
