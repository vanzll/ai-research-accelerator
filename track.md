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

## 2026-08-26 - Add coordinator-Goal and worker-relay control topology

- Corrected the overly broad Goal/relay exclusion: exclusivity is scoped to one
  conversation and unresolved objective, not the entire distributed job.
- Added the supported hybrid topology in which a Node 0 coordinator Goal owns
  global recovery through first-work validation while ordinary-mode worker
  agents are woken by token-free relays for bounded node-local requests.
- Standardized a star-shaped control plane: workers report to the coordinator;
  only the coordinator publishes shared code, assets, retry manifests, and
  cross-node requests. Workers do not command one another.
- Strengthened the shared-file protocol with fencing epochs, immutable inbox
  requests, acknowledgements, terminal results, request deduplication, and an
  explicit ban on executing arbitrary request text from a watcher.
- Recorded the hybrid's boundary: shared-file changes cannot wake a blocked
  coordinator Goal, so a long coordinator wait requires an explicit ownership
  handoff to an ordinary coordinator relay.
- Independent review caught that the existing generic relay is one event per
  generation and does not monitor a dynamic structured inbox. The protocol now
  requires a separately reviewed repeated-request dispatcher, keeps manifest
  consumption and gang retries supervisor-owned, and reserves relays for
  judgment or repair events.
- Added an atomic coordinator lease with a fencing epoch, frozen coordinator
  identity, exact sender/target validation, and worker-owned per-request ACK and
  result records to prevent duplicate coordinators and ambiguous completion.
- Disallowed in-attempt coordinator takeover; coordinator loss creates a new
  attempt and fencing epoch.
- Added an experiment-scoped lock-owning publisher and atomic
  `active-attempt.json`. Workers re-check it before accepting commands or
  starting training, so superseded coordinators cannot revive an old attempt.
- Defined at-least-once wake delivery with expiring claims. Requests are not
  processed until terminal results exist; ACK-without-result is escalated to the
  coordinator, and task retries require new request IDs.
- Clarified that supervisors observe first work while the coordinator Goal owns
  recovery decisions through that gate, and that Node 0's local worker remains
  supervisor-owned rather than creating a second Node 0 agent.
- Added `long_task_relay.py defer-finalize` so a resumed agent can durably
  request acknowledgement and optional re-arming after the synchronously
  delivering watcher exits; direct in-turn rearm was impossible by lifecycle.
- Fenced deferred finalization by generation, event ID, and watcher PID, reused
  matching live helpers, and added regression coverage preventing stale helpers
  from changing a newer relay generation.
- Raised the plugin version to `0.3.5`.

## 2026-08-26 - Implement repeated coordinator-to-worker agent dispatch

- Added `shared_agent_dispatcher.py`, an attempt-scoped shared-filesystem
  message bus for a Node 0 Goal coordinator and ordinary-mode worker threads.
- Node 0 atomically publishes bounded requests; worker dispatchers validate the
  coordinator, target host, attempt, nonce, contract hash, fencing epoch, and
  request ID before resuming the exact `$CODEX_THREAD_ID`.
- Added worker-owned claims, ACKs, terminal results, request deduplication,
  transcript-idle checks, structured agent output, and conservative handling of
  accepted-but-incomplete tasks.
- Added regression tests for repeated delivery, deduplication, stale-request
  rejection, immutable manifests, and duplicate coordinator ownership.
- Independent review found the initial epoch check was self-referential. Added
  a lock-advanced authority record so a higher epoch fences both stale
  publishers and stale dispatchers.
- Replaced synchronous resume with a gate-controlled helper process group. ACK
  now means Codex was actually spawned; helper identity, start token, claim
  lease, bounded idle wait, crash recovery, stop cleanup, and terminal result
  ownership are mechanically tested.
- Closed review-discovered takeover, close, and stop races with quiescent
  authority locks, worker-local stop serialization, and a child-owned lock
  inherited by the actual Codex process. Fault tests now kill both helper and
  dispatcher while Codex is active and verify that a newer epoch cannot begin.
- Updated the relay and multi-node skills so Node 0 Goal plus Node 1--N relay is
  the default shared-storage collaboration pattern; workers no longer use Goal
  mode or poll shared files with model tokens.
- Raised the plugin version to `0.3.6`.

## 2026-08-26 - Tighten first-mile worker bootstrap acceptance

- A real four-node handoff exposed a bootstrap paradox: worker prompts ran
  before the shared tool checkout existed, accepted a transient waiter PID,
  and ended without any dispatcher. The later fixed script could not wake the
  worker because the missing dispatcher was itself the wake mechanism.
- The relay and multi-node skills now require coordinator-first publication of
  the tool, manifest, and final node scripts; workers must execute those scripts
  and prove an exact live dispatcher in `watching` state before returning.
- Added a mandatory two-round harmless request/response smoke before training
  may depend on the agent bus. Raised the plugin version to `0.3.7`.

## 2026-08-26 - Validate and clarify shared-filesystem agent coordination

- The four-node workflow completed exact-thread delivery from the Node 0 Goal
  coordinator to all three ordinary worker agents, terminal result return, and
  repeated dispatcher re-arming through the shared filesystem.
- Added explicit evidence boundaries for `AGENT_BUS_READY`, `TASK_DISPATCHED`,
  node/cluster readiness, and actual training startup. A successful bus smoke
  no longer implies that a formal training command has been published.
- Defined `watching` with no active request as healthy idle state rather than a
  blocked Goal or failed pipeline, and required request action inspection rather
  than relying on aggregate ACK/result counts.
- Added token-free bus monitoring guidance over heartbeat, inbox, claim, ACK,
  result, and invocation state. Historical failures remain preserved but are
  filtered by active attempt, fencing epoch, and expected request IDs.
- Kept the proven star topology: Node 0 is the sole command publisher, workers
  execute bounded requests and return structured evidence, and worker-to-worker
  needs are routed back through the coordinator.
- Synchronized Codex and Claude plugin manifests at version `0.3.8`.
