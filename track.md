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
