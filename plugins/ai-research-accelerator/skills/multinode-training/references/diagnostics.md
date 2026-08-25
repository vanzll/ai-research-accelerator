# Multinode Diagnostics

Diagnose the last completed launch stage before changing training settings. A flat reward curve cannot explain a job that never reached the trainer.

## Stage 1: asset preparation

Symptoms:

- model process alive but no service port;
- Hugging Face lock files or network connections;
- blobs present but snapshot path incomplete;
- only one node reaches readiness.

Checks:

- inspect the exact model path passed to the loader;
- verify required snapshot files and symlink targets;
- inspect lock owner and process I/O;
- confirm only the coordinator can write shared assets;
- confirm workers use offline/local-only loading after readiness.

Do not fix this by increasing the service timeout before proving useful progress.

## Stage 2: node-local service startup

Symptoms:

- process exists but health endpoint is absent or invalid;
- one node reports a different model revision or GPU mapping;
- reward requests hang after the trainer starts.

Checks:

- process group, child process, log freshness, port owner, health response, GPU memory, and heartbeat;
- node-local endpoint configuration on every trainer rank;
- request and response counts, latency, timeout, and error rate.
- inspect the service child's environment for leaked training rendezvous
  variables; libraries such as Accelerate or Transformers may initialize a
  process group during model construction even when the service was intended
  to be local and single-process.

## Tracker startup versus step-zero evaluation

If a run identity exists locally but cloud history is empty, reconstruct the order of events: tracker initialization, lightweight startup-row log and flush, full evaluation, first optimizer step, and termination. A formal step-zero evaluation can be much longer than a smoke evaluation. A cloud-visibility deadline that starts before the first lightweight history row is committed measures evaluation duration, not tracker health.

Do not repair this by merely extending one hard timeout. Emit the startup row before evaluation, validate the tracker query against a real row, and keep tracker degradation separate from training liveness.

## Stage 3: rendezvous

Symptoms:

- workers wait before the first distributed log;
- connection refused, timeout, address already in use, or only one node appears.

Checks:

- identical master address/port, rendezvous ID, node count, and process count;
- unique node ranks and expected hostnames;
- private-network DNS/IP reachability and firewall rules;
- stale master process or port owner from an earlier attempt.

## Stage 4: collective initialization or runtime hang

Symptoms:

- all ranks start but stop at initialization, backward, metric reduction, or checkpoint;
- some ranks exit while others stay at 100% or 0% GPU utilization.

Checks:

- rank-prefixed enter/exit logs around the suspected collective;
- same process group and collective order on all ranks;
- empty or uneven batches causing branch divergence;
- rank-0-only code accidentally calling a collective;
- correct network interface and transport.

Use `NCCL_DEBUG=INFO` and `TORCH_DISTRIBUTED_DEBUG=DETAIL` for a bounded reproduction. NCCL auto-selects interfaces; set `NCCL_SOCKET_IFNAME` only after identifying the correct cross-node interface. Persistent debug logging can be expensive and should not silently remain in formal runs.

Before blaming model code, compare the selected NCCL transport with the frozen
contract. Look for `NET/IB` versus `NET/Socket`, inherited
`NCCL_IB_DISABLE=1`, nonexistent interface names, active RDMA devices that NCCL
never opens, and asymmetric interface availability across hosts. Run a bounded
collective benchmark outside the model. It should fail before training if the
required transport is absent. A finite slowdown triggers diagnosis unless the
run contract declares a previously validated hard transport floor.

If RDMA is selected but identical probes alternate between fast and extremely slow paths, identify the loaded `libnccl.so`, not just the reported version. Vendor NCCL/KCCL builds can share an ABI/version with the wheel-bundled NCCL while implementing different multi-rail policy. Verify the resolved library path and checksum before changing HCA lists, QP counts, GID indices, traffic classes, or topology.

Use tensor collectives and one atomic result record per rank or pair for bandwidth diagnosis. Python object collectives add serialization and are not a bandwidth oracle; concurrent multi-rank stdout can interleave and corrupt parsers even when the collective itself is healthy.

## Stage 5: correctness mismatch

Symptoms:

- multi-node loss differs unexpectedly from single-node;
- reward/advantage statistics change when only topology changes;
- W&B values equal one rank's local values;
- sample count is smaller than configured world-size scaling predicts.

Checks:

- derive DP replica count and global batch from the full parallel mesh;
- verify loss scaling and gradient accumulation boundaries;
- inspect semantic K-group placement and normalization population;
- reduce weighted numerators and denominators, not unweighted rank means;
- verify scheduler, EMA, clipping, and optimizer advance once per intended update.
- test backend adapter APIs with the exact runtime argument shapes. In generative pipelines, a list of per-sample RNG generators may require one draw per sample rather than being forwarded to an API that accepts only one generator.

## Stage 6: OOM or throughput regression

Separate rollout/inference, forward, backward, optimizer, evaluation, reward service, and checkpoint peaks. Record per-rank allocated/reserved peaks and identify the maximum rank.

Classify an OOM as capacity, fragmentation, or co-location pressure before
changing the algorithm. Cached `reserved` memory is not phase attribution, and
an allocator hint is not a substitute for enough headroom. Account for
node-local reward/eval services on the same GPU, and test the exact first
backward because rollout success does not prove update memory fits.

For performance, measure:

- samples or tokens per second globally;
- maximum and distribution of rollout, reward, forward/backward, collective, optimizer, evaluation, and checkpoint time;
- communication-to-compute ratio;
- data and asset I/O wait;
- GPU utilization and memory by phase;
- straggler rank and node.

`nvidia-smi` utilization can be misleading during communication waits. A GPU
may report 100% utilization while power draw and memory-controller activity are
near idle because NCCL/CUDA wait kernels remain resident. Compare step latency,
power, memory-controller utilization, transport logs, and a known single-node
baseline. Repeated slow steps rule out one-time compilation warmup.

If single-node FSDP is fast but the same configuration collapses after adding a
node, inspect both layers in order: first transport correctness, then shard
geography. Full-world sharding can amplify a TCP fallback because parameter
all-gathers cross nodes at every layer; node-local HSDP may reduce that traffic,
but it is not a substitute for repairing RDMA.

Optimize only after correctness. Prefer increasing useful local work or overlap before adding nodes when inter-node communication dominates.

For a throughput probe, a finite slow step is a result, not a failed health
gate. Use a wide timeout only to distinguish progress from a genuine hang, and
collect enough post-warmup steps to compare medians.

## Failure report

A useful report states:

- last completed stage and first missing evidence;
- affected nodes/ranks and exact attempt/nonce;
- whether trainer, W&B, optimizer step, and checkpoint ever started;
- primary log/process/network evidence;
- cleanup status and remaining owned/unowned processes;
- root cause versus direct trigger;
- the contract change required before a new attempt.

Do not describe a timeout as the root cause when the actual cause is an incomplete asset, missing node, asymmetric collective, or dead service.

Also distinguish training failure from control-plane failure. A healthy run can be falsely rejected by a broken attempt parser, duplicated validator, tracker query, log parser, or liveness race. Before changing model code, reconstruct the timeline from immutable optimizer-step records, rank-local logs, terminal statuses, and tracker history.
