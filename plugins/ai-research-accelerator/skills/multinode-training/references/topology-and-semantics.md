# Topology and Training Semantics

Read this reference before changing world size, parallelism, batching, sample grouping, gradient accumulation, or checkpoint logic.

## Name every parallel axis

Do not describe a job only as "16 GPUs." Record the mesh explicitly:

- **DP:** independent data-parallel replicas that contribute different examples and synchronize gradients;
- **FSDP/ZeRO:** data-parallel replicas whose parameters, gradients, or optimizer state are sharded;
- **TP:** ranks that jointly compute tensor operations for one model replica;
- **PP:** ranks that own different model stages;
- **SP/CP:** ranks that split sequence or context tokens from the same sample;
- **EP:** ranks that own different experts.

The total world size is the product of the independent mesh dimensions. The number of independent examples processed concurrently is generally the DP dimension, not the world size.

Write the intended identity explicitly, for example:

```text
world_size = dp * tp * pp * cp
global_batch = dp * local_batch_per_dp_replica * gradient_accumulation
```

Adjust the expression when pipeline schedules, packed sequences, or framework-specific accumulation change the semantics. Verify it from runtime metrics rather than trusting configuration names.

## Preserve estimator groups

RL and preference estimators often require K samples from one prompt or state. Define:

- which rank owns each sample;
- where K samples are gathered;
- whether normalization is prompt-local, replica-local, or global;
- whether covariance, advantage, or reward statistics are computed before or after cross-rank aggregation;
- which population paper-facing metrics summarize.

A generic `DistributedSampler` partitions examples; it does not guarantee that semantic groups remain contiguous or complete. Add a group-aware sampler or explicit gather when required.

## Gradient accumulation is not automatically equivalent

Gradient accumulation preserves a larger effective batch only when:

- the loss reduction and scaling match the non-accumulated formulation;
- optimizer, scheduler, clipping, EMA, and logging advance only at the intended optimizer boundary;
- stochastic layers and sample-dependent normalization do not change the estimator;
- per-microbatch reward or advantage normalization is not substituted for global normalization;
- all-reduce/no-sync behavior is correct.

For on-policy RL, accumulating optimizer gradients across separately generated policy versions is usually not equivalent. Freeze the rollout policy and estimator inputs for the complete accumulated update if equivalence is claimed.

## Rank and collective semantics

- `LOCAL_RANK` selects the local device.
- `RANK` identifies a process in the current worker group.
- `WORLD_SIZE` is the current number of processes.
- `NODE_RANK` is launcher metadata for a static node allocation.

Elastic restart or membership change can recreate the worker group with different global ranks. Use experiment ID, attempt, launch nonce, hostname, and a process start identity for durable lineage.

Every collective must be called by exactly the expected process group in the same order. Common deadlocks include:

- rank 0 enters a collective save while other ranks exit;
- one rank skips a metric reduction because its local batch is empty;
- an exception is swallowed on one rank while peers enter the next barrier;
- different parallel groups call similarly named collectives in different orders.

## Metrics must match the scientific population

Choose and label reductions deliberately:

- local rank metric;
- node mean or maximum;
- DP-replica mean;
- all-rank mean;
- prompt-group mean;
- sample-weighted global mean.

For reward curves, gather the numerator and denominator or use a correctly weighted reduction. Averaging rank means is biased when ranks contribute different sample counts.

For timing, report both global maximum and distribution across ranks. The slowest participating rank determines synchronized throughput.

## Checkpoint contract

Classify checkpoint contents by ownership:

- model shards and optimizer shards: collective, all required ranks participate;
- scalar training state and metadata: one designated writer after collective completion;
- dataloader/RNG state: store per rank when exact resume requires it;
- success manifest: written last, after a final agreement that all expected files exist.

Do not declare a checkpoint valid from directory existence alone. Validate shard count, expected ranks, training step, config/commit identity, and loadability with the intended world-size policy.
