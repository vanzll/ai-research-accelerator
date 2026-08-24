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

## Stage 6: OOM or throughput regression

Separate rollout/inference, forward, backward, optimizer, evaluation, reward service, and checkpoint peaks. Record per-rank allocated/reserved peaks and identify the maximum rank.

For performance, measure:

- samples or tokens per second globally;
- maximum and distribution of rollout, reward, forward/backward, collective, optimizer, evaluation, and checkpoint time;
- communication-to-compute ratio;
- data and asset I/O wait;
- GPU utilization and memory by phase;
- straggler rank and node.

Optimize only after correctness. Prefer increasing useful local work or overlap before adding nodes when inter-node communication dominates.

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
