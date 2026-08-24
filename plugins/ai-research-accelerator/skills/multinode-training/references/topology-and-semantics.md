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

Also record where each mesh dimension lives physically. For FSDP/HSDP, state
the shard degree, replicate degree, ranks in each shard group, and whether a
group crosses node boundaries. For example, on two eight-GPU nodes:

```text
full-world FSDP: shard_degree=16, replicate_degree=1
node-local HSDP: shard_degree=8, replicate_degree=2
```

These can preserve the same global gradient semantics while having very
different communication schedules. Full-world sharding materializes parameter
shards across nodes at many layer boundaries; HSDP keeps shard collectives
within a node and synchronizes replicated shard groups across nodes. Do not
choose between them from GPU count alone. First verify the interconnect, then
benchmark the exact model topology and account for memory, optimizer state,
gradient reduction, and framework mesh semantics.

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

## Serialize a larger logical batch only when explicitly requested

Fewer GPUs can reproduce a larger parallel logical batch by spending more wall time, but this is an opt-in execution mode. Use it only when the user explicitly asks to trade speed for algorithmic equivalence or requests a target logical batch/topology that cannot run concurrently. Otherwise keep the fastest correct parallel schedule; do not silently serialize work because resources are scarce.

First freeze the target contract, for example `P16/K4 = 64 videos per optimizer update`. Then partition that logical batch into serial waves. A single wave's physical microbatch is an execution detail; the estimator and optimizer must still observe the complete logical batch.

Two implementations are possible:

1. **Materialize then train:** generate all waves from one frozen policy snapshot, retain trajectories and old-policy statistics on CPU or storage, then train over update microbatches.
2. **Stream and accumulate:** generate one or more complete estimator groups, backpropagate their correctly scaled losses, discard trajectories, and continue without changing parameters until the logical batch is complete.

Streaming is equivalent only if pending gradients do not affect forward behavior and every invariant below holds:

- policy parameters, rollout policy, reference model, reward model, and estimator definition stay fixed across all waves;
- no optimizer, scheduler, EMA, KL-controller, moving-anchor, scaler-growth, or checkpoint step advances between waves;
- each K-sample prompt/state group is complete before its reward, advantage, covariance, or other group statistic is computed;
- old log probabilities, latent trajectories, timesteps, masks, and conditioning remain paired with the exact rollout that produced them;
- independent samples use the intended RNG semantics; accidental seed reuse must not collapse group diversity;
- each microbatch loss is weighted so the accumulated gradient equals the mean over the full logical population, including uneven final microbatches;
- gradient clipping, optimizer stepping, scheduler stepping, and zeroing occur once at the declared optimizer boundary;
- cross-wave metrics are reduced with sample-count weighting, and W&B distinguishes rollout wave, generated samples, and optimizer step;
- any batch-dependent stochastic layer or normalization that would differ under serialization is disabled, frozen, or acknowledged as breaking exact equivalence;
- the smoke executes every serial wave and one real optimizer step. A one-wave smoke cannot validate this mode.

Increasing microbatch size uses more memory and may improve throughput; increasing the number of accumulated microbatches increases the logical batch. Do not conflate these controls.

Before launch, report both the equivalence claim and its cost. Include generated samples, rollout waves, optimizer steps, wall time, and GPU-hours in comparisons. Serialization may preserve the estimator while substantially changing throughput; optimizer-step curves alone can conceal that cost.

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
