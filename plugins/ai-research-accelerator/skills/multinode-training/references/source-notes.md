# Authoritative Sources and Adoption Baseline

This skill combines official framework guidance with operational lessons from real research clusters. Refresh source-dependent claims when framework behavior changes.

GitHub star counts below were queried on 2026-08-24 and are included only as a rough adoption signal, not as evidence of technical correctness.

## PyTorch

- Repository: [pytorch/pytorch](https://github.com/pytorch/pytorch), about 102.6k stars on 2026-08-24.
- [PyTorch Distributed Overview](https://docs.pytorch.org/tutorials/beginner/dist_overview.html): choose DDP when a replica fits on one GPU, FSDP when it does not, and combine TP/PP when sharded data parallelism reaches scaling limits.
- [Multinode Training Tutorial](https://docs.pytorch.org/tutorials/intermediate/ddp_series_multinode.html): launch the same rendezvous on every node; distinguish local and global ranks; inter-node communication can dominate; diagnose TCP and network-interface selection.
- [torchrun Elastic Launch](https://docs.pytorch.org/docs/stable/elastic/run): a worker failure restarts or terminates the worker group according to the configured policy; rank assignment is not stable across elastic membership changes.

Rules derived: explicit topology, rank-safe logic, gang failure, bounded rendezvous, and no durable identity based only on global rank.

## Hugging Face Accelerate

- Repository: [huggingface/accelerate](https://github.com/huggingface/accelerate), about 9.8k stars on 2026-08-24.
- [Launching Accelerate Scripts](https://huggingface.co/docs/accelerate/main/basic_tutorials/launch): code, data, environment, node rank, main address, and port must agree; the launch command runs on every node; private-network master addresses are preferred.

Rules derived: identical frozen configuration on all nodes, unique machine rank, per-node launch, and a configuration test before formal training.

## DeepSpeed

- Repository: [deepspeedai/DeepSpeed](https://github.com/deepspeedai/DeepSpeed), about 43.0k stars on 2026-08-24.
- [DeepSpeed Getting Started](https://www.deepspeed.ai/getting-started/): hostfiles declare hosts and slots; no-SSH mode still requires the same hostfile, unique node rank, master address, and port on every node; distributed environment variables must be propagated deliberately.

Rules derived: a machine-readable host inventory, explicit slots, symmetrical environment propagation, and launcher-owned node roles.

## Megatron-LM

- Repository: [NVIDIA/Megatron-LM](https://github.com/NVIDIA/Megatron-LM), about 17.6k stars on 2026-08-24.
- [Megatron-LM repository](https://github.com/NVIDIA/Megatron-LM): production-scale training composes data, tensor, pipeline, context, and expert parallel dimensions; gradient finalization synchronizes across the relevant groups.

Rules derived: name every mesh dimension, compute independent data replicas rather than equating GPUs with samples, and preserve collective-group semantics.

## Hugging Face Hub assets

- [Cache layout](https://huggingface.co/docs/huggingface_hub/guides/manage-cache): refs, blobs, and snapshots have distinct roles; blob presence alone does not establish a complete snapshot.
- [Environment variables](https://huggingface.co/docs/huggingface_hub/en/package_reference/environment_variables): `HF_HUB_OFFLINE=1` disables Hub HTTP calls and must be set before imports that read the setting.
- [Hub utilities](https://huggingface.co/docs/huggingface_hub/package_reference/utilities): local-only loading can explicitly report missing or incomplete snapshots.

Rules derived: single-writer asset preparation, immutable verified snapshots, explicit paths, and offline fail-fast worker loading.

## NVIDIA NCCL

- [Networking Troubleshooting](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/troubleshooting/networking_troubleshooting.html): NCCL auto-detects network interfaces, but an interface that is up and not cross-node reachable can cause initialization failure or hangs; `NCCL_SOCKET_IFNAME` can select the intended interface.

Rules derived: verify networking before tuning it, use bounded debug reproductions, and avoid cargo-cult NCCL environment changes.
