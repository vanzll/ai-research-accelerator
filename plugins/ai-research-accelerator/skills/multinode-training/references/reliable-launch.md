# Reliable Multinode Launch Protocol

Read this reference before writing launchers, supervisors, remote-agent prompts, asset preparation, or recovery logic.

## Separate the coordinator from workers

The coordinator controls one-time cluster state. Workers execute node-local preparation and the frozen distributed command.

On shared storage, the coordinator is the only writer for shared code bundles, model assets, datasets, and launch manifests. Workers do not download, repair, or mutate shared caches concurrently. On non-shared storage, the coordinator prepares a manifest and each worker stages and verifies its own immutable copy.

The coordinator is not allowed to report startup success until every expected node has passed the same stage.

## Durable state machine

Use attempt-scoped paths and advance monotonically:

```text
RESERVED
  -> ASSETS_READY
  -> NODE_LOCAL_READY for every node
  -> CLUSTER_READY
  -> TRAINING_STARTED
  -> FIRST_WORK_VALIDATED
  -> COMPLETED or FAILED
```

Every record should be atomic JSON or equivalent structured data, not an unqualified `touch` file. Include at least:

```json
{
  "schema_version": 1,
  "experiment_id": "...",
  "attempt": 2,
  "launch_nonce": "...",
  "commit": "...",
  "node_rank": 1,
  "hostname": "...",
  "state": "NODE_LOCAL_READY",
  "timestamp_utc": "..."
}
```

Include relevant asset-manifest hash, config hash, service endpoint, process-group ID, or W&B run ID at later stages. Readers must reject stale records whose experiment ID, attempt, nonce, commit, or expected hostname does not match.

## Asset protocol

### Shared filesystem

1. The coordinator takes a single-writer lock with bounded acquisition time.
2. It downloads to a temporary directory that is not a valid model path.
3. It pins an immutable revision and validates required files, sizes, and checksums when available.
4. It publishes the final directory or manifest atomically.
5. It writes `ASSETS_READY` last.
6. Workers verify the same manifest and then load only from explicit paths.

For Hugging Face assets, a blob may exist while the snapshot is incomplete. Verify the actual directory passed to `from_pretrained`. Once prepared, set offline mode before Python imports and pass `local_files_only=True`. Formal training must fail immediately if an asset is missing instead of entering a network/cache lock path.

If Xet or HTTP/2 is incompatible with a site proxy, only the coordinator may switch to a bounded, resumable HTTP/1.1 or Range-download path. Verify the final size and checksum before publication. This is a transport fallback, not permission for workers to download concurrently.

### Non-shared filesystem

Distribute the verified asset bundle or use the same pinned download manifest on every node. Each node writes its own `NODE_ASSETS_READY` only after local verification. Cluster readiness requires all nodes.

## Node-local services

Reward models, data servers, and evaluators often run once per node. For each service:

- bind an explicit local GPU and port;
- use an attempt-scoped cache and log when shared mutation is unsafe;
- record the owning PID and process group;
- verify the process is alive;
- verify the application endpoint returns a valid response;
- refresh a heartbeat or expose a health endpoint;
- clean up only processes owned by the current attempt.

Port listening alone is insufficient if the service can accept TCP before model loading finishes. A process alone is insufficient if it is blocked on a model cache lock.

## Rendezvous and launch

- Resolve the master through the cluster's private network.
- Verify every node uses the same `MASTER_ADDR`, `MASTER_PORT`, `NNODES`, run ID, and rendezvous ID, with a unique node rank.
- Check that the master port is free before the attempt and reachable when the rendezvous is intentionally active.
- Launch all nodes within a bounded window. A durable launcher or scheduler should do this; a conversational agent should not manually race commands.
- Start workers in their own process groups. Cleanup must terminate the complete owned group, including children left after a launcher exits.
- Propagate exceptions and signals into a cluster-wide failure record. Do not leave peers blocked in a collective.

Use a static rendezvous for a fixed research run unless elastic membership and checkpoint-resume semantics have been explicitly designed and tested.

## First-work validation

Do not wait until job completion to discover a partial launch. While all workers are alive, require:

- every expected global rank joined;
- the runtime topology matches the frozen contract;
- one complete global batch or rollout was consumed;
- at least one optimizer step completed with finite loss and gradients;
- global sample/group counts and globally reduced metrics match expectations;
- any tracker declared by the run contract created the exact run identity and logged the expected step;
- a distributed checkpoint smoke succeeds when formal training will save checkpoints.

Write `FIRST_WORK_VALIDATED` only after these checks. A remote coding agent may end its turn after a deterministic supervisor owns the job and this evidence is either produced or will mechanically fail within a bounded deadline.

## Resource and cleanup hooks

Treat cluster-specific resource leases such as GPU reservation commands as configurable hooks, not universal commands. The launcher must:

- acquire or release resources at the correct point;
- install cleanup traps before starting owned services or workers;
- restore the site's idle/lease state after success, failure, signal, or crash where possible;
- avoid stopping unowned processes without explicit authorization.

## Retry policy

Preserve logs, state records, and failed markers. Diagnose and repair the cause before retrying. Use a new attempt number and launch nonce; never make a failed lineage appear successful by deleting evidence. Reuse immutable assets only after they pass the repaired validation contract.

## Remote-agent prompt contract

A send-and-forget prompt must give the remote agent:

- exact host identity and role;
- repository, branch, exact commit, clean-checkout requirement, and config/experiment IDs;
- complete topology and rendezvous values;
- asset ownership: coordinator prepares, worker verifies, no fallback network download;
- bounded preflight, service readiness, heartbeat, and first-work gates;
- process-group ownership and cleanup hooks;
- durable logs and marker paths;
- failure behavior and retry prohibition;
- a stopping rule: hand off to a deterministic supervisor after validation, without model-driven polling.

The prompt is incomplete if the user must stay awake to notice that nothing launched.
