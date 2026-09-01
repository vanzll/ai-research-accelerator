# Development Track

## 2026-08-31: Harden pinned patch publication

- Extended `multinode-training` after a successful four-node recovery exposed
  two remaining dependency-contract gaps: a generated external patch was
  validated by its preparer but rejected by a stale runtime hash guard, and a
  detached checkout could publish a different local branch than its current
  training commit.
- Compatibility patches are now treated as executable build artifacts: produce
  them from real checkout states, validate the fully applied result, and update
  every identity consumer together. Detached publication must use an explicit
  source ref and verify the remote commit before worker staging.
- Existing guidance already covered the other retrospective findings, including
  Gloo for Python object collectives, fenced GPU leases, final-shell environment
  activation, fixed result schemas, low-noise failure parsing, persistent
  dispatchers, and deterministic monitoring, so those rules were not duplicated.

## 2026-08-30: Add contract-driven fresh-context feature development

- Added `contract-driven-feature-development` for substantial new algorithms,
  cross-module work, shared core paths, and other regression-sensitive changes.
- The main thread freezes a concise contract and integrates the result. A fresh
  implementation Agent works in an isolated worktree, while a different fresh
  reviewer receives the contract, diff, references, and tests without the
  implementer's reasoning or desired verdict.
- The workflow is deliberately risk-routed: small local edits bypass it, broad
  archaeology is not a default phase, and only hardware/distributed behavior
  that cannot be validated locally requires one real smoke.
- The rule was distilled after a shared video-training compatibility patch
  encoded an invalid SP follower assumption and a source-string test locked in
  that behavior. The skill therefore requires behavior-level regressions and
  explicit isolation of existing behavior behind default-off feature switches.
- Raised the dual Codex/Claude plugin version to `0.8.0` and added the new skill
  plus `continuous-skill-learning` to repository validation.

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

## 2026-08-26 - Make first-mile dispatcher ownership explicit

- Audited the four bootstrap failures against the skill. Coordinator-first
  publication, conjunctive `watching` acceptance, and the self-bootstrap
  deadlock were already represented; durable process ownership was only
  implicit and has now been made mandatory.
- Worker dispatchers must run under tmux, a scheduler, a service manager, or an
  equivalent owner that survives the worker Agent turn. An ordinary background
  child or momentarily live bootstrap PID is not sufficient.
- Worker readiness now requires all checks simultaneously: persisted
  `state.json`, matching PID/start identity and exact thread/config, a live
  dispatcher under its durable owner, and status exactly `watching`.
- Explicitly documented that a missing dispatcher cannot wake the Agent needed
  to install it. Such a first-mile failure requires the foreground worker turn
  to repair it or an external actor to re-enter the worker.
- Removed the conflicting worker-before-coordinator `waiting-for-manifest`
  path; coordinator assets and final bootstrap scripts must exist first.
- Raised the synchronized plugin version to `0.3.9`.

## 2026-08-26 - Extract shared-filesystem Agent coordination

- Added `shared-filesystem-agent-coordination` as a standalone primary skill
  for multi-session and multi-host Agent collaboration independent of GPU
  training.
- Moved the general star topology, coordinator-first bootstrap, durable worker
  dispatcher, atomic request/claim/ACK/result protocol, fencing, exactly-once
  terminal processing through at-least-once delivery and request-ID
  deduplication, monitoring, repair authority, and closure guidance into the new
  skill and its protocol reference.
- Reduced `multinode-training` to its domain integration: scientific-contract
  protection, coordinator ownership of shared training assets and retries,
  semantics-preserving repair, and independent distributed first-work evidence.
- Kept the reviewed dispatcher implementation in `long-task-relay` so delivery
  has one deterministic implementation rather than duplicate copies; the relay
  skill now points back to the standalone coordination protocol.
- Registered seven primary skills and raised the synchronized plugin version to
  `0.4.0`.

## 2026-08-27 - Bind worker dispatchers to the campaign

- A real A2-to-A3 recovery exposed that attempt-scoped dispatchers exited on
  A2 terminal before A3 consumers existed, recreating the first-mile deadlock
  despite successful within-attempt message delivery.
- Corrected the lifecycle model: dispatcher registration, heartbeat, and close
  are campaign/Goal-scoped; request data, process ownership, failure evidence,
  and terminal results remain attempt-scoped.
- Added atomic active-attempt adoption under the campaign fencing epoch. An
  attempt failure returns workers to `watching`; only explicit Goal/campaign
  completion closes the communication channel.
- Added make-before-break compatibility for the current attempt-root
  dispatcher: create and validate the successor through the old bus before
  closing the old attempt.
- Restricted normal dispatcher shutdown to one authenticated, fenced
  `GOAL_COMPLETED` directive from the exact Node 0 coordinator. Attempt/request
  failure, idle time, workload exit, or temporary coordinator loss now means
  safe waiting; abnormal process death is supervisor-restarted rather than
  interpreted as Goal completion.
- Raised the synchronized plugin version to `0.4.1`.

## 2026-08-27 - Implement campaign-persistent Agent dispatchers

- Added a real campaign control layer to `shared_agent_dispatcher.py` instead
  of relying on attempt-scoped lifecycle prose: immutable campaign manifest,
  compare-and-swap active attempt, stable worker state, durable restart
  supervisor, and fenced `GOAL_COMPLETED` closure.
- Attempt terminals now return the same dispatcher process to `watching`.
  A2-to-A3 adoption preserves worker thread and dispatcher identity; stale or
  invalid attempt pointers enter a non-executing wait rather than exiting.
- Bound Goal completion to the expected final root, attempt, nonce, contract,
  Node 0 host/thread, and fencing epoch. Completion drains active Agent work,
  prevents queued work from starting, and blocks later publish, activation, or
  supervisor restart.
- Added campaign binding records so attempt-level publish rejects a completed
  campaign. Fixed attempt publication order so an immutable manifest exists
  before authority advances.
- Added regression coverage for cross-attempt persistence, invalid-pointer
  recovery, abnormal dispatcher restart, stale compare-and-swap rejection, and
  active/queued completion races. Preserved all existing attempt-level tests.
- Clarified that host/thread/epoch checks are identity fencing under a trusted
  shared-filesystem threat model; untrusted writers require ACLs or signatures.
- Raised the synchronized plugin version to `0.5.0`.

## 2026-08-27 - Remove worker conversation lifetime from campaigns

- Replaced exact-thread resume as the campaign default with one fresh,
  ephemeral Codex invocation per bounded request. Persistent shared records and
  repository handoffs are now worker memory; a TUI thread ending or being
  replaced no longer breaks Node 0-to-worker delivery.
- Retained exact-thread resume only as an explicit compatibility adapter with
  a pinned transcript and `CODEX_HOME`; reusable campaign bootstraps must not
  hard-code TUI threads or use `--last`.
- Froze and persisted the worker adapter, Codex executable, Codex home, work
  directory, and extra arguments. Dispatcher-owned prompt/result arguments
  cannot be overridden.
- Preserved the campaign lifecycle across attempts: a durable node owner keeps
  the campaign supervisor alive, the supervisor restarts the dispatcher, and
  only the dispatcher creates short-lived Agents. Only fenced Goal completion
  closes those persistent layers.
- Fixed a concurrent-start race in which a live supervisor whose dispatcher
  state had not yet appeared could be mistaken for an absent supervisor.
- Added tests for fresh invocation arguments and environment, explicit resume
  compatibility, reserved-argument rejection, and idempotent startup through
  the supervisor/dispatcher state publication window. The full repository now
  passes 46 tests.
- Raised the synchronized plugin version to `0.6.0`.

- During remote rollout review, fixed another distributed-control boundary:
  `campaign-status` now returns unknown liveness when queried from a different
  host, and `campaign-stop` refuses remote-host PID control. Worker-local
  short-TTL attestations plus end-to-end request results are the coordinator's
  remote readiness evidence. This correction is released as `0.6.1`.

## 2026-08-27 - Distill the first successful 32-rank campaign lessons

- Reviewed the persisted Flow-ART retrospective after the stateless Agent Bus
  reached a real four-host, 32-rank rollout. Kept the evidence boundary clear:
  Agent coordination and rollout infrastructure worked, while finite optimizer
  updates and scientific acceptance remained unproven.
- Separated durable control artifacts by role: immutable protected task contract,
  campaign identity, dynamic active attempt/fencing state, bounded request,
  and versioned result schema. Existing runbooks and progress documents remain
  optional human context. Prompts now refer to canonical authority instead of
  duplicating stale attempt lore.
- Required one pinned deterministic preflight/validator implementation. Worker
  Agents interpret and repair evidence but do not recreate parsers or hard-code
  retry numbers; validators compare current authority plus canonical identity
  or content hashes.
- Split worker actions into quick preflight/start results and token-free domain
  observation. A fresh Agent no longer waits for a long evaluation or
  optimizer-step acceptance after it has proved the exact process launched.
- Added reusable bus acceptance keyed to dispatcher tool, durable owner, host,
  adapter, campaign authority, and live dispatcher generation so unchanged task
  retries do not pay for repeated Agent transport smoke while restarts are
  revalidated.
- Added mechanism-neutral code reachability validation through the wrapper's
  actual staging/import path, progress-aware collective deadlines, TOCTOU-safe
  process cleanup, and phase-specific co-located reward/trainer memory analysis.
- Raised synchronized Codex and Claude plugin manifests to `0.6.2`.

## 2026-08-30 - Fence worker readiness to the exact campaign

- A remote Flow-ART launch exposed a stale-control-plane acceptance bug: Node1
  had a healthy `watching` dispatcher for an older UR2POINT campaign, and a
  generic worker check incorrectly treated it as readiness for the new
  distilled campaign.
- Clarified that a campaign is the control-plane namespace for one coordinator
  Goal and one immutable protected contract across retries. A healthy process
  from another campaign has no authority over the current experiment.
- Worker acceptance now explicitly binds the canonical campaign root and ID,
  protected/science-contract hash, coordinator authority, node/host,
  dispatcher generation and process identity, execution adapter, and current
  attempt root/ID/nonce/fencing epoch. Arbitrary `state.json` discovery is
  forbidden.
- Added the same invariant to multinode cluster readiness and documented
  make-before-break migration: validate the expected new campaign before
  retiring an old campaign under its own closure authority.
- Added validated campaign-transition hygiene: before a new workload starts,
  every host retires only identity-matched old owners, dispatchers, Agents, and
  domain process groups; active requests drain first. Dead-owner PID files,
  sockets, locks, and incomplete temporary state may be removed, while logs,
  manifests, requests/results, markers, checkpoints, and failure lineage remain
  preserved. Broad process kills, cache deletion, and concurrent shared-state
  cleanup by workers are explicitly prohibited.
- Added an environment-boundary rule after the distilled asset handoff exposed
  that a runner could require a model path without giving its downloader the
  user's proxy/Hugging Face environment. The user/cluster bootstrap is now a
  declared launch-contract field and must be sourced inside every independent
  asset-download, tmux/scheduler, dispatcher, probe, service, evaluator, and
  trainer child shell. Prompts must name it explicitly; secret values are
  checked only for presence and never logged or serialized to shared state.

## 2026-08-30 - Add evidence-gated continuous skill learning

- Added `continuous-skill-learning`, a meta-skill that runs after user
  corrections, avoidable retries, evidence-backed reversals, reusable review
  findings, and validated recoveries. It explicitly models persistent learning
  as skill/script/test improvement rather than model-weight training.
- The workflow records primary evidence, tests generality, and then chooses
  delete, replace, narrow, extend, relocate, create, or no change. It prefers
  correcting and pruning the narrowest existing skill; a new skill is reserved
  for a distinct reusable capability.
- Added a decision rubric that separates verified, supported, and speculative
  lessons; derives failure/cause/invariant/mechanical-check statements; limits
  per-incident change size; and requires periodic consolidation.
- Added workspace-level automatic triggering so a qualifying lesson audit runs
  after the primary task is stable without another user reminder. Learning does
  not expand permissions, encode secrets, or silently change scientific/user
  semantics.
- Synchronized the installed runtime skill, validated both source and installed
  copies, and raised the plugin version to `0.7.0`.

## 2026-08-30 - Fence node-level GPU reservation cleanup across attempts

- A verified overlapping-attempt failure showed that attempt-local cleanup
  idempotency is insufficient: a retired attempt exited after its successor had
  started and unconditionally restored the node's idle GPU reservation,
  injecting an occupancy process into the live successor.
- Replaced the ambiguous “restore on exit” guidance with a node-level fenced
  lease invariant. Acquisition advances an owner/generation under a local lock;
  cleanup restores idle state only when its owner/generation remains current
  and no successor lease is active. Stale cleanup is an evidenced no-op.
- Added the required regression ordering: A acquires, B supersedes, A exits
  late without restoring idle state, then B exits and restores it exactly once;
  duplicate signals and dead recorded owners are also covered conceptually.

## 2026-08-30 - Distill the accepted Distilled32 A15 retrospective

- Read the complete campaign retrospective covering avoidable A3--A15 time
  sinks and retained project-specific history in the campaign record rather
  than copying it into general skills.
- Existing skills already covered generation-fenced GPU leases, explicit child
  environment sourcing, hard attempt terminals/cleanup, immutable retry
  lineage, campaign host identity, and first-work acceptance evidence.
- Added missing reusable rules: Python object metadata uses only an explicitly
  dedicated Gloo group (ambiguous/mixed/NCCL-capable groups are unsafe), while
  large numeric payloads use tensor collectives; backend-report variants need
  CPU-focused tests.
- Added a diffusion conditioning-shape contract: classic CFG may save paired
  unconditional/conditional rows, whereas distilled guidance-one paths may be
  conditional-only; update adapters reject mixed/unexpected optimizer-window
  row layouts without synthesizing unused branches.
- Tightened asset staging with a same-child-context no-secret connectivity
  probe plus index/shard metadata parsing before atomic publication.
- Tightened long-run monitoring to structured counters and parsed health values;
  raw progress bars are fallback evidence and a healthy metric key containing
  `nonfinite` must never be treated as an error without evaluating its value.

## 2026-08-30 - Correct continuous-learning topic scope

- User feedback identified scope creep: the Distilled32 retrospective directly
  belonged to multinode training, but one monitoring lesson was also appended
  to `long-task-relay` based only on adjacent relevance.
- Removed that unrelated cross-skill edit. The multinode diagnostic rule stays
  with the owning workflow.
- Added a strict topic-ownership gate to continuous learning: a target skill's
  core capability must directly own the failed decision and primary evidence
  must show its guidance or implementation contributed. One incident updates
  one owning skill by default; incidental co-occurrence or possible usefulness
  cannot justify modifying neighboring skills.

## 2026-08-31 - Add labeled Edge-to-Overleaf editing

- Added `edit-overleaf-with-edge` for direct editing of a signed-in Overleaf
  project through the user's Edge extension.
- Every completed logical edit batch now requires an Overleaf History label in
  the form `Codex YYYY-MM-DD HH:MM TZ | summary` after a successful explicit
  compile. Transient visual iterations share the final batch label.
- Figure, table, equation, and page-layout edits require inspection of the
  latest right-hand PDF preview and iterative correction before labeling.
- The workflow detects an authoritative active GitHub paper PR before editing
  so Overleaf and Git do not silently diverge, and it leaves the final compiled
  page visible for author review.

## 2026-08-31 - Add Overleaf polish mode

- Added a Reviewing-mode workflow for author-written tracked changes. Codex can
  refine English or translate Chinese drafts into concise academic English while
  preserving claims, notation, citations, and paragraph intent.
- Polish mode creates a `before polishing` label before touching tracked changes,
  accepts only the reviewed target scope, recompiles and visually checks the
  affected pages, then creates a `polish and accept` final label.
- Project-wide `Accept all` is prohibited when unrelated collaborator changes
  may exist. Ambiguous scientific or mathematical changes remain unaccepted for
  author clarification.
- Git synchronization stays paused while tracked changes are active because a
  Git push can lose or displace Overleaf revisions and comments.

## 2026-08-31 - Process complete author reviews from one instruction

- `处理我的 review` and `process my review` now trigger a complete pass over
  the active Overleaf project's pending user-authored tracked changes and
  unresolved comments without requiring the author to restate the scope.
- English edits are polished, Chinese edits are translated into natural
  academic English, and tracked deletions retain their intended semantics.
- User comments are treated as scoped paper-editing instructions. Fully
  implemented comments are resolved only after compilation and PDF inspection;
  ambiguous, blocked, or partially handled comments remain unresolved.
- The workflow never accepts unrelated collaborator changes, uses global
  `Accept all`, deletes comments, or treats a document comment as permission for
  unrelated browser actions.

## 2026-08-31 - Time-box ordinary Overleaf review processing

- Author feedback showed that the safe review workflow could become inefficient
  through repeated skill reads, duplicate UI expansion, local-Git rescans, and
  unchanged-state polling after the full review batch was already known.
- Added a fast path for small text-focused batches: one inventory/source
  capture, one classification pass, one coherent edit batch, and one compile
  plus affected-page inspection, targeting roughly ten minutes.
- The workflow now stops rediscovery once sufficient live source is available
  and falls back from an incomplete Review-panel diff to the corresponding live
  source range after one reasonable attempt. History checkpoints, scoped
  acceptance, and comment-resolution safeguards remain mandatory.

## 2026-08-31 - Close review-inventory and local-edit gaps

- A review pass took about 31 minutes because the initial inventory treated the
  visible cards as complete, discovered two items only after expanding `More
  comments`, replaced the full manuscript for two local cross-references, and
  retried review actions after Overleaf had invalidated their node identifiers.
- The fast path now requires exhausting `More comments` before editing, prefers
  targeted replacements for local corrections, and reacquires review cards once
  after each destructive action instead of retrying stale identifiers.

## 2026-08-31 - Refactor Overleaf editing into a batch-first workflow

- Replaced the accumulated review instructions with one staged workflow:
  complete inventory, one rollback label, one coherent edit batch, one compile
  and affected-page check, one browser-side comment-resolution loop, and one
  final label.
- Established a single-writer rule for the live Overleaf project. Large reviews
  may parallelize analysis over frozen, disjoint source snapshots, but only the
  coordinator may edit, compile, resolve comments, or label History.
- Added explicit 5--10 minute expectations for ordinary single-file text
  reviews, prohibited full-manuscript replacement for local fixes, and required
  comment-node reacquisition inside one browser tool call rather than through
  repeated model round trips.

## 2026-09-01 - Prefer direct coordinator execution before an Agent bus

- A four-node allocation probe showed that the coordinator could execute
  bounded SSH commands on every worker through their private IP addresses and
  verify the expected remote hostname/user, while the equivalent FQDN forms
  failed authentication. Requiring every alias to succeed incorrectly marked a
  usable control path as failed.
- Multinode guidance now separates connection endpoints from remote identity,
  accepts one platform-approved endpoint after command-level host/user
  attestation, freezes that endpoint per worker, and defaults to one coordinator
  plus deterministic worker supervisors when direct execution is available.
  In this mode only Node 0 receives a Goal prompt; worker nodes need no Coding
  Agent, and shared storage carries evidence rather than Agent messages. A
  shared Agent bus remains appropriate only for independent worker judgment or
  when no direct executor exists.

## 2026-09-01 - Add replaceable allocation launcher backends

- Multinode launch guidance now separates scientific commands, a generic
  foreground node wrapper, and thin allocation adapters such as MPI, Slurm,
  direct SSH, or a platform operator. Backend selection is explicit and
  hostfiles/site variables remain adapter inputs rather than generic runner
  requirements.
- A verified scheduler-native launcher is preferred over direct SSH, with an
  Agent bus last. MPI must first pass a no-GPU allocation/rank probe; its initial
  integration uses one unbound foreground wrapper per node and the existing
  local torchrun, keeping the outer launcher in the master supervisor for exit
  propagation and gang cleanup. A user-requested launch prompt therefore goes
  only to the master/Node 0 Goal Agent.
