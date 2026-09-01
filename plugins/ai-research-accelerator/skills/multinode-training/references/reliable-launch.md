# Reliable Multinode Launch Protocol

Read this reference before writing launchers, supervisors, remote-agent prompts, asset preparation, or recovery logic.

## Separate the coordinator from workers

The coordinator controls one-time cluster state. Workers execute node-local preparation and the frozen distributed command.

On shared storage, the coordinator is the only writer for shared code bundles, model assets, datasets, and launch manifests. Workers do not download, repair, or mutate shared caches concurrently. On non-shared storage, the coordinator prepares a manifest and each worker stages and verifies its own immutable copy.

The coordinator is not allowed to report startup success until every expected node has passed the same stage. This role need not be a complex service: on a fixed two-node run, an atomic shared contract plus one launcher per node is often sufficient.

Before adding a cross-node Agent control plane, test whether the coordinator
already has bounded authenticated command execution to every worker. Treat the
connection endpoint and the remote host identity as separate facts: one
platform-approved endpoint may be an IP address, scheduler address, SSH alias,
or FQDN, and a failed optional alias does not invalidate a successful endpoint.
Accept the route only when the remote command returns the expected hostname and
user, then freeze that working endpoint per worker. Do not require every alias
form to authenticate, and do not infer identity from the connection string
alone. When this direct route exists and worker actions are deterministic, use
one coordinator with node-local supervisors instead of an Agent bus.

## AI-agent collaboration over shared storage

Use the `shared-filesystem-agent-coordination` skill for the general Agent Bus,
first-mile bootstrap, coordinator/worker modes, message protocol, stateless
worker execution, optional resume adapters, monitoring, and repair loop. The training integration adds these
constraints:

- the protected contract is the scientific run contract, including algorithm,
  model/reward/data identities, batch/group and optimizer semantics, precision,
  sampling, parallel mesh, evaluation, and checkpoint behavior;
- Node 0 alone publishes shared code, assets, run contracts, and retries;
  workers verify them and may repair only semantics-preserving node-local state;
- the coordinator Goal owns global recovery only through
  `FIRST_WORK_VALIDATED`; deterministic supervisors own waiting and trainers;
- worker dispatchers are campaign/Goal-scoped and survive failed run attempts;
  only attempt requests, processes, and evidence terminate on an attempt end.
  Normal dispatcher shutdown requires Node 0's fenced `GOAL_COMPLETED` record;
- `AGENT_BUS_READY` and request results are sidecar control evidence. They do
  not replace `NODE_LOCAL_READY`, `CLUSTER_READY`, `TRAINING_STARTED`, or
  `FIRST_WORK_VALIDATED` evidence;
- every shared operational repair needs a regression test, new commit, and new
  attempt/nonce. An uncertain semantic effect requires user approval.

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

These are evidence boundaries, not a requirement to build one daemon or file
per state. A simple fixed run can use one atomic status record plus immutable
first-work and terminal milestones. Implement only states that change a real
recovery decision.

`AGENT_BUS_READY` and each request's dispatch/ACK/result lifecycle are
control-plane sidecar evidence, not extra stages in this experiment state
machine. Agent requests may occur before or between several experiment stages;
they must never be used as substitutes for those stages' primary evidence.

Every record should be atomic JSON or equivalent structured data, not an unqualified `touch` file. Milestones such as `FIRST_OPTIMIZER_STEP` are immutable: write a new step-specific record rather than rewriting one liveness file. Include at least:

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

Include relevant asset-manifest hash, config hash, service endpoint, process-group ID, or W&B run ID at later stages. Readers must reject stale records whose experiment ID, attempt, nonce, commit, or expected hostname does not match. Mutable heartbeats may supplement milestones, but must never erase already established facts.

## Code staging and validator contract

Publishing code means proving that every worker can obtain the exact immutable
artifact through the same staging path the formal wrapper will use. Before GPU
release:

1. identify the actual mechanism: Git ref, source bundle, container image,
   scheduler package, shared worktree, or copied tree;
2. publish an immutable identity containing every runner and training artifact;
3. exercise that mechanism in each distinct worker credential/network domain,
   or reuse fresh evidence whose artifact, path, and domain identities match;
4. verify submodules, nested repositories, image digest, or bundle manifest when
   the wrapper uses them;
5. verify the final checkout/import path consumed by the wrapper, not merely a
   coordinator staging location;
6. record the staging probe and artifact/contract hashes.

For Git, a fresh clone or fetch followed by detached checkout is the strongest
reachability probe. `git cat-file -e` proves only that one object database
contains an object. Equivalent non-Git flows should verify their own immutable
digest and extraction/import path instead of being forced through Git.

If frozen source is assembled through one or more compatibility patches,
generate those patches from actual before/after checkout states rather than
hand-writing nested hunks. Apply the full chain once to a clean pinned checkout,
exercise the repaired runtime path, and compute the identity from the resulting
tracked diff or tree. Keep one temporary checkout while iterating instead of
recreating it for each hunk. Search for every consumer of that identity and
update its expected value in the same change, including preparation scripts,
launch validators, and runtime import guards.

A detached checkout has no current local branch to push implicitly. Publish an
authorized repair with an explicit source ref such as `HEAD:<target-branch>`,
then verify that the remote branch resolves to the intended commit before any
worker stages it. A successful push command that names only a local branch does
not prove that the detached training commit was published.

Keep one pinned preflight implementation and a versioned result schema in Git.
Agents run it and interpret its result; do not ask every worker to construct a
new parser in its prompt. Validators read attempt and fencing values from the
active authority record, compare canonical paths or content hashes, and reject
unknown schemas. Retry state must advance the validator's dynamic input, not
require edits to a hard-coded attempt number.

## Asset protocol

### Discover and import before download

Asset preparation starts with bounded discovery, not network access. Check the asset roots declared by the run contract, prior verified manifests, project checkpoint directories, and explicitly configured shared caches. Do not scan an entire shared filesystem without a bounded path and timeout.

A missing canonical manifest means the candidate is unverified; it does not mean the model is absent. For every candidate:

1. identify the exact files the loader will consume, including weight indexes and all referenced shards;
2. verify model identity and immutable revision where metadata permits;
3. verify required files, sizes, and checksums against an authoritative index or pinned manifest;
4. reject mixed revisions, incomplete snapshots, dangling links, and paths that would trigger a fallback network lookup;
5. if valid, atomically import it into the canonical layout using hard links or read-only symlinks when safe, then generate the new manifest;
6. download only the files that remain absent or invalid.

Record whether each asset was reused, imported, repaired, or downloaded. A launcher that redownloads an already verified multi-gigabyte model because it lives under a different cache layout is defective: it wastes time, bandwidth, and storage and adds a new failure path without improving reproducibility.

Never equate one cache implementation with model identity. A project-local checkpoint tree and a Hugging Face snapshot can contain the same immutable files. Reproducibility comes from verifying content and revision, not from forcing every valid asset through one cache directory.

### Shared filesystem

1. The coordinator takes a single-writer lock with bounded acquisition time.
2. Inside the final asset-preparation child shell, it sources the declared
   user/cluster environment bootstrap and verifies required proxy,
   authentication, and toolchain variables without logging their values.
   Before a large transfer, run a bounded no-secret connectivity probe in this
   same child context; a successful interactive parent probe is insufficient.
3. It performs the discovery-and-import protocol above.
4. If network transfer is still required, it downloads to a temporary directory that is not a valid model path.
5. It pins an immutable revision and validates required files, sizes, and checksums when available.
   For sharded tensor formats, also parse the weight index and each shard's
   format metadata/header before publication so a truncated or malformed file
   cannot pass a pathname/size-only gate.
6. It publishes the final directory or manifest atomically.
7. It writes `ASSETS_READY` last.
8. Workers verify the same manifest and then load only from explicit paths.

For Hugging Face assets, a blob may exist while the snapshot is incomplete, but the inverse mistake is also dangerous: a complete model in a project checkpoint directory must not be treated as absent merely because no Hugging Face snapshot pointer or new manifest exists. Verify the actual directory passed to `from_pretrained`. Once prepared, set offline mode before Python imports and pass `local_files_only=True`. Formal training must fail immediately if an asset is missing instead of entering a network/cache lock path.

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

Process scans are inherently TOCTOU-racy. If a PID disappears between listing
and reading `/proc/<pid>`, do not fail teardown solely on `ESRCH`; record an
unexpected earlier exit when applicable and verify that no owned descendants or
process-group members remain. Still fail on a live process whose identity or
ownership does not match.

Treat the service process as a hard environment boundary. Remove training-only
rendezvous variables such as `RANK`, `WORLD_SIZE`, `LOCAL_RANK`,
`LOCAL_WORLD_SIZE`, `GROUP_RANK`, `ROLE_RANK`, `MASTER_ADDR`, and
`MASTER_PORT` before importing frameworks that may auto-initialize distributed
state. Do this only for the service child. The trainer must retain its frozen
rendezvous environment.

Port listening alone is insufficient if the service can accept TCP before model loading finishes. A process alone is insufficient if it is blocked on a model cache lock.

## Rendezvous and launch

- Resolve the master through the cluster's private network.
- Verify every node uses the same `MASTER_ADDR`, `MASTER_PORT`, `NNODES`, run ID, and rendezvous ID, with a unique node rank.
- Check that the master port is free before the attempt and reachable when the rendezvous is intentionally active.
- Launch all nodes within a bounded window. A durable launcher or scheduler should do this; a conversational agent should not manually race commands.
- Start workers in their own process groups. Cleanup must terminate the complete owned group, including children left after a launcher exits.
- Propagate exceptions and signals into a cluster-wide failure record. Do not leave peers blocked in a collective.

Prepare the environment inside the final shell that `exec`s each trainer, probe,
or service. Verify the child process's interpreter, launcher, import roots, and
loaded communication library against a small allowlisted fingerprint; never
record credentials. A parent-shell check does not prove what tmux, a container,
or a relay actually inherited.

Declare one user/cluster environment bootstrap path in the launch contract
(for example, a site-provided shell setup file). Source it explicitly inside
every independent asset-preparation, download, tmux, scheduler, dispatcher,
probe, service, evaluator, and trainer child shell before environment checks or
network access. Do not assume an SSH parent, interactive Agent, or login shell
exported proxy, authentication, Conda, CUDA, or vendor communication settings
to a later child. Validate required secret-bearing variables by presence only,
redact command tracing, and never serialize their values into logs, manifests,
prompts, or the shared Agent bus. Source first, then remove training rendezvous
state from children such as reward services that must not inherit it.

Process-group ownership needs a handshake. `setsid command &` followed by one
immediate `ps` is racy: `setsid` may fork, or the parent may inspect the child
before session creation. Use a non-forking child wrapper that publishes its
PID/PGID after setup, or poll the intended invariant with a short bounded
timeout while also checking child liveness. Do not release GPUs or report
readiness until ownership is established.

Each node supervisor should consume nonce-bound terminal failure records and
terminate only this attempt's local process group. Treat one missed heartbeat
or failed query as `SUSPECT`; require bounded repeated failure or an explicit
peer terminal record before gang cleanup.

## Transport preflight

Treat the communication implementation and transport as part of the frozen run contract, not ambient shell state. Perform a fresh probe when this identity is unknown or changed; otherwise reuse a matching frozen report. When probing:

1. inspect the actual active interfaces and RDMA HCAs on every host;
2. resolve the actual communication library before tuning transport. Inspect the library path loaded by a bounded process (`/proc/<pid>/maps`, loader diagnostics, or an equivalent check), record its checksum, and explicitly preload a pinned site NCCL/KCCL build when the platform requires one. The reported NCCL version or ABI is not enough;
3. discard undeclared inherited transport variables, then explicitly restore
   the complete platform-approved contract. This may include the network
   plugin, library preload, HCA/GID selectors, cross-NIC policy,
   `NCCL_IB_DISABLE`, and `NCCL_SOCKET_IFNAME`; never preserve arbitrary parent
   values with shell defaults or erase required vendor settings;
4. run a small multi-node tensor collective using the exact host/rank/GPU topology. For pairwise HSDP/replica traffic, cover every physical cross-node pair rather than only one world-wide average;
5. capture bounded `NCCL_DEBUG=INFO`/`NCCL_DEBUG_SUBSYS=NET` evidence and verify
   the final transport selection (for example, `Using network IB`), not merely
   device discovery; reject a later `Using network Socket` when RDMA is
   required;
6. repeat the probe when the observed failure is intermittent. One fast run is not evidence that a random slow path has been removed;
7. record the result in an attempt-scoped report keyed by hosts, topology,
   library checksum, network policy, and probe code. Fail on a throughput floor
   only when it is a predeclared, previously validated platform requirement;
   otherwise a finite slow result triggers diagnosis, not automatic failure.

Report payload or algorithmic bandwidth separately from NCCL bus bandwidth;
their conversion depends on collective and world size. Run the probe in an
owned process group so cancellation, timeout, or peer failure cannot leave
workers holding GPUs or rendezvous ports.

Use separate no-progress and absolute deadlines. Refresh progress only from
meaningful evidence such as completed phases, new rank joins, or structured
communicator activity; ordinary log noise is insufficient. A second clean
process-group construction can expose intermittent initialization failures and
should be retained when that is the risk being tested, but it need not be
repeated for an unchanged, recently accepted transport identity. If progress
continues, allow the predeclared hard deadline rather than killing at the short
stall threshold. If no progress occurs, fail early and preserve the last phase.
Do not respond to a premature timeout by deleting the validating round.

Never copy an interface name from another backend or cluster without checking that it exists on every target host. If the probe falls back to TCP when RDMA is required, fail before model loading. If it selects RDMA but remains intermittently slow, verify the loaded NCCL/KCCL implementation before cycling through HCA, QP, traffic-class, or GID tuning. After transport is correct, profile the parallel mesh separately; do not conflate a transport failure with an FSDP topology decision.

For a reusable launcher, make this discovery internal to the launch rather than requiring a separate user-operated probe. Each node should publish an atomic topology report; the coordinator should derive an immutable contract from all expected reports; workers should validate their own slice; then the exact world should run a bounded collective and directly enter the formal trainer. Cache or reuse collective evidence only after recollecting the live topology and matching host order, world size, GPU/HCA affinity, HCA ports/rates, GID/netdev mapping, driver/runtime identity, communication-library path and checksum, logical mesh, and probe shape against an immutable prior report. Bind the acceptance to the new contract hash. Any mismatch falls back to a fresh probe; never copy the prior contract and assume the allocation is unchanged. Unknown vendor libraries are not candidates unless the platform explicitly allows them.

Do not repeat a costly transport matrix for each formal attempt when a frozen report already matches all relevant identities. At launch, verify the report hash and communication-library checksum instead.

Use a static rendezvous for a fixed research run unless elastic membership and checkpoint-resume semantics have been explicitly designed and tested.

## First-work validation

Do not wait until job completion to discover a partial launch. Require:

- every expected global rank joined, recorded at the distributed barrier or optimizer boundary;
- the runtime topology matches the frozen contract;
- one complete global batch or rollout was consumed;
- at least one optimizer step completed with finite loss and gradients;
- global sample/group counts and globally reduced metrics match expectations;
- distributed checkpoint behavior has matching evidence when formal training will save checkpoints. Reuse an earlier exact-topology checkpoint smoke unless checkpoint code, format, topology, or storage changed.

Write immutable per-node completion records at the optimizer boundary, then derive `TRAINING_FIRST_WORK_VALIDATED` from distributed evidence. Track cloud visibility separately as `TRACKER_VERIFIED`. Do not require tracker visibility and instantaneous worker PID counts to be true in the same poll: cloud history is asynchronous and workers may legitimately enter teardown. The durable distributed milestone proves rank participation; tracker verification proves observability.

Test the exact tracker API query against a real minimal run before making it a kill condition. Projected history queries can omit a valid step zero depending on API behavior; a false-negative telemetry probe must not terminate otherwise healthy training. After a bounded visibility wait, record an `OBSERVABILITY_DEGRADED` state and preserve training unless the frozen experiment contract explicitly requires fail-closed telemetry.

Tracker startup, evaluation, and training health are separate states. Use this telemetry sequence:

1. initialize the exact tracker run identity;
2. immediately log and flush a lightweight startup row containing experiment ID, nonce, commit, topology, and a telemetry-started flag;
3. persist local `STARTUP_ROW_COMMITTED` evidence with the tracker run ID;
4. verify cloud visibility asynchronously;
5. after the local startup commit, begin expensive step-zero evaluation when practical. Cloud verification continues in parallel and must not sit on the critical path of model evaluation or training.

Do not treat a locally written startup marker as proof that cloud history exists, and do not wait for a full evaluation to create the first history row. A fixed tracker timeout must never kill a healthy job merely because a formal evaluation has many prompts. If visibility remains unavailable, record `OBSERVABILITY_DEGRADED`, retain local logs and tracker identity, and follow the experiment's explicit telemetry policy.

Do not call a smoke healthy until a real optimizer step is finite. A smoke evaluation should use the smallest fixed prompt subset that exercises the same path; it must not run a full paper evaluation suite before validating basic throughput. A health smoke may use a generous hang deadline so a job that is hundreds of times slower cannot occupy a cluster for days. A throughput experiment, however, must not classify “slower than expected” as failure; bound only genuine hangs and retain the measured slow result. Once an exact-topology smoke has already established this evidence, a formal launcher should start directly and perform only the early handshake; it should not run another smoke or promotion stage.

## Resource and cleanup hooks

Treat cluster-specific resource leases such as GPU reservation commands as configurable hooks, not universal commands. The launcher must:

- acquire or release resources at the correct point;
- install cleanup traps before starting owned services or workers;
- restore the site's idle/lease state after success, failure, signal, or crash
  only when the exiting owner still holds the current node-level lease;
- avoid stopping unowned processes without explicit authorization.

Resource ownership is node-scoped and can outlive or overlap an attempt. Guard
transitions with a node-local lock and persist the campaign/attempt owner,
process identity, and monotonically increasing lease generation. Starting a
successor atomically advances that generation before releasing the idle
reservation. An attempt's EXIT trap submits a conditional release: it restores
the idle reservation only if its owner/generation still matches and no current
successor workload is active. Otherwise it records a stale-cleanup no-op. Do
not implement this as an unconditional `gpu_hold`, a process-name scan, or a
per-attempt `cleanup_done` flag; those mechanisms cannot prevent an older
attempt from overwriting a newer attempt's resource state.

Test at least this ordering for a reusable hook: attempt A acquires, attempt B
supersedes A, A exits late, and the idle reservation remains absent while B is
active; when B exits, the idle state is restored exactly once. Also test
duplicate signals and a dead recorded owner. Cleanup evidence should include
the requested owner/generation, observed current owner/generation, and whether
the transition was applied or rejected, without exposing unrelated processes.

## Retry policy

Preserve logs, state records, and failed markers. Diagnose and repair the cause before retrying. Use a new attempt number and launch nonce; never make a failed lineage appear successful by deleting evidence. Reuse immutable assets only after they pass the repaired validation contract.

When agents are authorized to repair and continue unattended, that authority
does not include scientific changes. The coordinator may repair control-plane,
communication, environment, telemetry, or semantics-preserving compatibility
bugs; workers submit evidence and requests. Revalidate the scientific contract
and runtime semantic quantities before publishing the next attempt. Validators
must account for framework lifecycle transformations and should check canonical
meaning rather than overloaded mutable argument names.

When the failure is an asset-layout mismatch, repair discovery/import logic before retrying. Do not solve it by creating another cache root and downloading the same revision again.

## Remote-agent prompt contract

A send-and-forget prompt must give the remote agent:

- exact host identity and role;
- repository, branch, exact commit, clean-checkout requirement, and config/experiment IDs;
- complete topology and rendezvous values;
- the exact user/cluster environment bootstrap that every independent child
  shell must source, including asset download and final tmux/scheduler shells;
- asset ownership: coordinator prepares, worker verifies, no fallback network download;
- bounded preflight, application readiness, and first-work gates;
- process-group ownership and cleanup hooks;
- durable logs and marker paths;
- failure behavior and retry prohibition;
- a stopping rule: hand off to a deterministic supervisor after validation, without model-driven polling.

For an explicitly authorized autonomous repair workflow, replace an absolute
retry prohibition with a narrow repair policy: list allowed operational bug
classes, freeze the scientific-contract hash, designate the coordinator as the
only shared-code publisher, require regression tests and new attempt lineage,
and define the shared event/inbox paths. State that scientific or uncertain
changes require user approval. Also state whether the prompt uses Goal mode or
ordinary relay mode; never assign both to the same unresolved objective.

The prompt is incomplete if the user must stay awake to notice that nothing launched.

An ordinary bootstrap or worker agent should exit after it has verified the
frozen supervisor, environment, cleanup trap, and tracker startup identity. The
token-free supervisor owns mechanical first-work observation and the formal
run. In the explicit coordinator-Goal hybrid, the coordinator Goal instead
retains decision and recovery ownership until `FIRST_WORK_VALIDATED`, then
completes; if it exits earlier, it must first hand that ownership to an ordinary
coordinator relay. Never leave the first-work response path ownerless, and never
make worker agents sleep and poll until an optimizer step or formal completion.
