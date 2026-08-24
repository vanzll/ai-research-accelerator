# HunyuanVideo 1.5 Two-Node KCCL Case Study

Use this case only when a vendor communication stack or similarly intermittent multi-rail failure is plausible. It is not a universal launch recipe.

## Failure stack

A two-node, 16-rank HunyuanVideo run used `SP=2`, `DP=8`, and HSDP with replicate degree 2 and shard degree 8. Eight independent cross-node replica pairs communicated concurrently. Failures appeared in layers:

1. the PyTorch wheel loaded its bundled NCCL/IBext instead of the cluster's xray KCCL build;
2. some cross-node paths fell from roughly 40--42 GiB/s to 0.011--0.044 GiB/s even though logs reported RDMA and the NCCL ABI/version matched;
3. HCA filtering, QP changes, single-rail selection, traffic-class changes, and host staging did not remove the intermittent slow path;
4. preloading the exact xray KCCL binary made two independent 32-case pair matrices consistently fast;
5. only after transport worked did launcher validation, Hunyuan generator-list compatibility, W&B visibility, and teardown races become observable.

The lesson is not "always preload KCCL." The lesson is that the resolved communication implementation is part of the environment contract, and one lucky fast probe does not establish an intermittent fault as fixed.

## Control-plane mistakes

Several failures were avoidable engineering defects rather than intrinsic distributed-training complexity:

- multi-digit attempt IDs were parsed by duplicated, inconsistent validators;
- Python object collectives and interleaved stdout were used as diagnostic data paths;
- runtime stdout was not durable from process start;
- a projected W&B step-zero query returned an empty result and killed healthy training;
- a later formal run wrote its local startup marker before a 31-prompt step-zero evaluation, but did not commit a lightweight W&B history row first. A 600-second cloud gate expired during the healthy evaluation and killed the job; the resulting run later appeared as crashed with zero history rows;
- node failure cleanup lacked a nonce-bound peer watchdog;
- one mutable liveness file was overwritten during normal rank teardown, erasing proof that all ranks had completed the target step.

Prevent these with one canonical validator, tensor-based probes, rank-local atomic logs, a real tracker API contract test, an immediate lightweight startup row before full evaluation, nonce/PID/PGID-scoped cleanup, and immutable per-step completion markers.

## Evidence reuse

After the exact 16-rank smoke completed three rollouts and six finite optimizer updates, another smoke was unnecessary. Formal training could reuse:

- the exact code/config/topology identity;
- the repeated KCCL matrix report and library checksum;
- verified asset manifests;
- the backend compatibility test;
- immutable first-work semantics.

The formal launcher should therefore start directly, preserve early failure cleanup, and expose a first-real-step handshake. Extra smoke or promotion layers would add control-plane failure modes without testing new scientific behavior.
