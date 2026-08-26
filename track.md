# Development Track

## 2026-08-21: Initial dual-agent plugin

- Initial repository/plugin name: `ai-for-academic-writing`; renamed to `ai-research-accelerator` before wider use.
- Display name: **AI Research Accelerator**. Tagline: **AI for Accelerating Research**.
- Distribution layout: one marketplace repository containing `plugins/ai-research-accelerator`, with both Codex and Claude Code manifests and shared Agent Skills.
- Main skills:
  - `write-insightful-topconf-paper`
  - `github-paper-review-workflow`
  - `manage-paper-experiments`
  - `plot-paper-experiments`
- Optional, unbundled integrations are documented in `README.md`: citation verification, Tavily research, scientific schematics/visualization, W&B, Apple Numbers, and PDF inspection.
- GitHub paper review uses Chinese semantic Markdown plus formal English LaTeX. Newest human review feedback has highest priority.
- Human and AI may use the same GitHub login. Every AI-authored GitHub message must contain `<!-- academic-writing-ai:... -->`; an unmarked message from an authorized login is treated as human instruction.
- The agent must not merge or resolve human review threads without explicit author approval.
- `collect_review_state.py` is read-only, defaults to private repositories, gathers all review surfaces, and fails closed when thread state is unavailable.
- Local validation passed:
  - `python scripts/validate_repo.py`
  - `python -m unittest discover -s tests -v`
  - Codex `quick_validate.py` for all four skills
  - Codex `validate_plugin.py`
  - `claude plugin validate .`
- Private GitHub repository after rename: `https://github.com/vanzll/ai-research-accelerator`.
- Initial published implementation commit: `94878f8ee42f618c7bbb24784d4a98bb46fad3ca`.
- GitHub Actions `Validate plugin` passed for the initial commit.
- A clean, isolated `CODEX_HOME` successfully installed the original package before rename; the renamed package is revalidated separately.

## 2026-08-21: Clean-context technical review gate

- Added a mandatory clean-context technical review for material scientific revisions and before paper PRs or submission candidates.
- The reviewer receives only the candidate artifact, minimal notation, and cited primary sources. Author intent, prior debate, suspected flaws, proposed fixes, and desired verdict are withheld to prevent answer leakage.
- Native model knowledge is used to detect possible errors, not as evidence. Source-dependent and unstable findings must be checked against primary sources or experiment records.
- The reviewer reports location-specific Blocker/Major/Minor findings; the writing agent adjudicates them and reruns the isolated review after material fixes. When a fresh context is unavailable, the gate must be reported as not run.
## 2026-08-21 - Add a cold-reader notation gate

- Updated `write-insightful-topconf-paper` locally and in the plugin source with a notation contract required before formula-heavy writing.
- The contract records each symbol's meaning, type, conditioning, frozen/current status, first definition, and collision risks.
- Before a paper PR, a clean-context reviewer must reconstruct this contract from the candidate alone; ambiguous or incorrectly reconstructed notation blocks the PR until revised.
- The rule also prohibits overloaded nearby symbols, unexplained stacked superscripts, and conflating sample targets, learned fields, population fields, and sampler fields.

## 2026-08-22 - Add token-free long-task relay

- Added `long-task-relay` as the Plugin's fifth primary skill and raised both
  Codex and Claude manifests to version `0.2.0`.
- Added a standard-library relay CLI that monitors logs, progress, durable
  markers, PIDs, and tmux sessions without invoking a model during polling.
- Delivery modes include exact Codex thread resume, a trusted generic resume
  command, PID-verified tmux TUI injection, and a durable inbox fallback.
- Relay state is atomic and versioned. Events are deduplicated by generation;
  thread-idle checks, bounded retries, backoff, heartbeat/status, acknowledgement,
  re-arm, cancellation, and synthetic delivery tests are included.
- The watcher is observation-only. It may summarize and deliver declared events
  but cannot interpret results, mutate code, or change task semantics. Fully
  authorized mechanical transitions remain the responsibility of a separately
  reviewed deterministic supervisor.
- `manage-paper-experiments` now explicitly composes this generic relay with
  experiment-specific W&B, queue, and GPU lifecycle contracts.
- Validation passed: 14 unit tests, repository validator, skill quick validator,
  Codex plugin validator, Python compilation, CLI help smoke, and `git diff --check`.

## 2026-08-24 - Add reliable multi-node training workflow

- Added `multinode-training` as the sixth primary skill and raised the Codex and
  Claude manifests to version `0.3.0`.
- Based the framework-facing guidance on official PyTorch/torchrun, Hugging Face
  Accelerate and Hub, DeepSpeed, Megatron-LM, and NVIDIA NCCL documentation.
- Added a three-contract model: computation topology, launch control plane, and
  external dependencies such as model assets and node-local reward services.
- Encoded a single-writer asset protocol: the coordinator downloads and verifies
  immutable assets, workers only verify, and formal training loads from explicit
  offline/local-only paths. Blob presence alone is not accepted as a complete
  Hugging Face snapshot.
- Cluster startup now requires nonce-bound readiness from every expected node,
  followed by one complete globally validated batch or rollout while workers and
  the exact W&B run are alive. Rank-0 readiness alone is explicitly insufficient.
- Added detailed references for topology and estimator semantics, reliable launch
  state and marker contracts, staged diagnostics, and source provenance.
- Validation passed for all 14 repository tests, the repository validator, the
  Codex skill and plugin validators, Claude plugin validation, JSON parsing,
  `git diff --check`, and live resolution of all 13 official reference URLs.

## 2026-08-25 - Refine multi-node assurance from HY1.5/KCCL failures

- Reclassified the launch ladder as proportionate assurance rather than a
  mandatory smoke/probe pipeline for every formal run. Exact-topology evidence
  may be reused when hosts, code, assets, topology, communication environment,
  and loaded library identity match.
- Added the loaded NCCL/KCCL binary path and checksum to the communication
  contract. The HY1.5 incident showed that wheel NCCL and xray KCCL reported the
  same ABI/version but differed by orders of magnitude on intermittent RoCE
  paths; repeated pair-matrix validation was required to establish the fix.
- Added control-plane lessons from A20--A25: canonical multi-digit attempt
  parsing, no duplicated validators, tensor-based transport probes, durable
  rank-local logs, tested W&B step-zero queries, nonce-scoped peer cleanup, and
  immutable optimizer-step evidence that cannot be erased during rank teardown.
- Clarified that after a matching smoke succeeds, formal training should launch
  directly with an early first-work handshake. Extra smoke/promotion machinery
  is justified only when it tests a changed contract.
- Initially recorded the cluster incident as a case study; its reusable rules
  were later absorbed into the normative references and the incident narrative
  was removed to keep the installed skill concise.
- Raised the plugin version to `0.3.1`; an independent clean-context review
  found no blockers and its four ambiguity findings were resolved before sync.
- A subsequent formal A25 failure exposed a distinct telemetry/evaluation race:
  the local W&B marker existed before a 31-prompt step-zero evaluation, but no
  lightweight history row had been committed. A 600-second cloud gate killed
  healthy evaluation. The skill now requires an immediate startup row before
  expensive eval and separates tracker degradation from training failure.
- Raised the plugin version to `0.3.2` for this correction.

## 2026-08-25 - Distill multi-node lessons into launch invariants

- Added mechanical topology arithmetic before node-count selection, including
  backend-specific SP/TP divisibility, DP population, global batch, and the
  distinction between throughput scaling and fixed-batch latency reduction.
- Clarified that gradient accumulation does not reduce one microbatch's peak
  memory and that rollout success does not prove the first backward will fit.
- Required environment and communication-library verification inside the final
  persistent child process instead of assuming parent-shell state is inherited.
- Separated tracker startup, cloud visibility, first optimizer work, and
  evaluation. A telemetry delay or a finite slow throughput result cannot kill
  healthy training unless a validated hard contract explicitly requires it.
- Simplified the control plane to one canonical validator, one node wrapper,
  and one deterministic token-free supervisor. Removed redundant promotion
  controllers, mandatory per-state daemons, agent polling, and the standalone
  HY1.5/KCCL incident narrative.
- Added nonce-scoped peer failure propagation, suspect-before-kill behavior,
  first-backward memory diagnosis, and application-level readiness checks.
- Raised the plugin version to `0.3.3`.

## 2026-08-26 - Separate Goal ownership from relay and add multi-agent repair

- Declared Goal mode and relay mode mutually exclusive for the same unresolved
  objective. An explicit Goal remains agent-owned; ordinary relay mode hands
  waiting to a token-free watcher and wakes a bounded agent only for events.
- Added a shared-filesystem multi-agent protocol for unattended multi-node
  repair: one coordinator publishes shared code and retry manifests, while
  workers preserve evidence, repair node-local operational state, and exchange
  atomic structured events, inbox requests, and acknowledgements.
- Repair authority is limited by an immutable scientific-contract hash.
  Operational fixes require regression tests, a new commit, and a new
  attempt/nonce; scientific or uncertain changes require user approval.
- Installed `long-task-relay` as a standalone local skill, synchronized the
  updated `multinode-training` skill locally, and raised the plugin version to
  `0.3.4`.
