# Production Runtime Promotion

Use this workflow before branching a new distributed algorithm/profile or
handing a launcher to a remote Agent. Its purpose is to close the loop from a
real incident to canonical executable code.

## Separate the states

An incident repair progresses through these states:

```text
OBSERVED
  -> EVIDENCE_VERIFIED
  -> REPAIR_VALIDATED_REMOTELY
  -> PROMOTED_TO_CANONICAL_RUNTIME
  -> REGRESSION_COVERED
  -> REQUIRED_BY_PROFILE
```

`Reviewed` or `SkillAbsorbed` does not imply `PROMOTED_TO_CANONICAL_RUNTIME`.
Do not launch a new profile while an applicable fix remains only in an attempt
checkout, conversation, retrospective, or non-descendant branch.

An attempt that has not reached its declared sustained-progress gate cannot
certify either a root cause or a successful repair. Its record must separate:

- `observed`: primary log, process, stack, metric, and timing evidence;
- `hypothesis`: the proposed causal explanation plus explicit confidence;
- `candidate_remedy`: the exact code/config delta being tested;
- `result`: the acceptance evidence, or `running-unvalidated` / failed stage.

Do not encode an unverified cause in an incident or fix ID. A successful retry
that changes two things validates only the combined candidate; it does not
identify which change was causal. Require a controlled differential when that
distinction affects what should be promoted. Until then, keep the candidate
pending and preserve competing explanations.

## One repository incident index

Keep one project-owned index under the repository root:

```text
踩坑记录/
  README.md
  ledger.json
  attempts/<experiment-id>/<attempt-nonce>.json
  receipts/<receipt-id>.json
```

Large logs remain in attempt storage and are referenced by path and hash. The
experiment ledger links an `incident_id`; the production manifest links the
same ID and promotion receipt; skills change only when the incident exposes a
reusable instruction defect. Do not copy the same narrative into multiple
ledgers.

Use a normal control checkout to maintain this tracked index, and launch from a
separate clean detached runtime worktree. A post-run docs commit may update the
index without being confused with the commit that actually trained.

Each repair record includes the prompt commit and secret-free command (or
tracked launch bundle plus hash), successful runtime commit and command,
optional docs-only commit, merge base, commit list, changed paths or diff hash,
pre/post science hashes, failed stage, evidence, root cause/confidence, tests,
W&B identity, and remaining uncertainty. Its disposition is one of `pending`,
`promoted`, `already-present`, `obsolete`, `site-specific`, `uncertain`, or
`rejected-scientific`.

## Build the canonical runtime

1. Freeze an incident-index generation and ingest only records added or changed
   since the last certified runtime. Do not rely on “latest run” when attempts
   may be concurrent.
2. For every new record, compare the prompt and successful runtime commits with
   Git: merge base, commit list, changed paths, and relevant patch. Classify
   each delta as applicable, already present, obsolete, scientific, uncertain,
   or site-specific.
3. Port or reimplement every applicable semantics-preserving fix on canonical
   main. Preserve attribution to the source attempt and commit. Do not merge a
   remote branch wholesale when it mixes science and operations.
4. Add a behavioral regression for the original failure. A source-string test
   is insufficient when the incident involved process lifecycle, rank
   divergence, asset identity, or parser behavior.
5. Run the incident regressions, frozen-path regressions, and any bounded real
   smoke that cannot be represented locally.
6. Update the root ledger and production-runtime manifest, commit and push the
   candidate, verify the remote ref can materialize it, and validate that exact
   candidate before writing its launch prompt.

Promotion should bracket feature work: establish a certified production base
first, implement the new feature on it, then perform one incremental pre-prompt
audit in case the incident generation advanced during development.

Before emitting a remote launch prompt, build a profile-specific incident
coverage matrix. For every applicable incident, name the canonical fix commit,
behavioral regression receipt, consuming launcher/profile, and launch-bundle
evidence. Generic permission to debug, a warning to monitor collectives, or a
reference to "the same steps as an earlier prompt" is not coverage. A prompt
must be self-contained, and a known incident that lacks executable coverage in
the supplied commit blocks delegation.

## Manifest contract

Store a repository-owned JSON manifest, for example
`runtime/production_runtime_manifest.json`:

```json
{
  "schema_version": 1,
  "runtime_id": "video-policy-production-v4",
  "incident_index": {
    "path": "踩坑记录/ledger.json",
    "generation": 12,
    "sha256": "<64-char SHA256>"
  },
  "canonical_runtime_commit": "<40-char canonical commit>",
  "accepted_runtime": {
    "commit": "<40-char accepted run commit>",
    "evidence_paths": ["<attempt retrospective or acceptance evidence>"]
  },
  "fixes": [
    {
      "id": "transport-log-short-hostname",
      "incident_id": "INC-0007",
      "status": "promoted",
      "source_prompt_commit": "<40-char original prompt commit>",
      "source_successful_commit": "<40-char accepted runtime commit>",
      "promoted_commit": "<40-char canonical promotion commit>",
      "source_evidence_paths": ["<incident evidence>"],
      "regression_tests": ["tests/test_transport_attestation.py"],
      "regression_receipt": "踩坑记录/receipts/transport-log-short-hostname.json",
      "required_for_profiles": ["*"]
    }
  ],
  "profiles": [
    {
      "id": "new-profile",
      "production_base_commit": "<same canonical runtime commit>",
      "required_fix_ids": ["transport-log-short-hostname"],
      "launch_bundle_path": "runners/new-profile/launch-bundle.json",
      "launch_bundle_sha256": "<64-char SHA256>",
      "science_contract_path": "runners/new-profile/science_contract.json",
      "science_contract_sha256": "<64-char SHA256>"
    }
  ]
}
```

The accepted runtime commit may be non-descendant. Each applicable repair must
then have a separate `promoted_commit` that is an ancestor of the launch
candidate. `required_for_profiles: ["*"]` prevents a new profile from silently
omitting a global production fix.

Validate before delegation:

```bash
python3 <skill>/scripts/validate_production_runtime.py \
  --manifest runtime/production_runtime_manifest.json \
  --repo . \
  --profile <profile-id> \
  --candidate-commit HEAD \
  --require-clean
```

The validator checks commit ancestry, fix promotion state, required regression
files, clean checkout, and the science-contract hash. Passing it does not run
the regressions; the release record must include their actual command and
result.

A production certificate is reusable only when its incident generation,
executable tree hash, manifest hash, validator version, regression receipt, and
independently frozen science baseline still match. Invalidate it for runtime,
launcher, dependency, schema, science-baseline, or newly applicable incident
changes. Do not invalidate it for unchanged prose or unrelated experiment
records. Dynamic host/process/capacity checks are never cached.

## Delegation gate

The coordinator's handoff names the validated manifest, profile, candidate
commit, validator output, regression report, and any remaining hardware-only
risk. Remote repair authority remains a fallback for genuinely new environment
failures. If the remote Agent rediscovers a manifest fix, treat that as a
release-gate defect and repair the canonical runtime before another profile is
launched.

The gate is not satisfied by ancestry or test-file existence alone. Require a
regression receipt from the exact executable candidate, evidence that the fix's
behavior remains present after later commits, a candidate-bound manifest and
launch bundle, preserved independent science hash, and remote reachability of
the named commit. No applicable or uncertain incident may remain pending.

Prefer an immutable `launch-bundle.json` containing normalized argv, relevant
non-secret environment, assets, topology, contract hashes, runtime commit, and
launcher digest. The remote prompt then carries the bundle path/hash, target
identity, one bootstrap command, repair authority, and success lifecycle instead
of duplicating stable launch details in prose.

Treat the bundle as the transitive executable trust root, not a list of obvious
entrypoints. Hash every repository-owned script, patch, config, and verifier
that the launcher or coordinator executes on the accepted path, including
indirect asset validators. Add a profile test that fails when a required
executable is absent from the bundle; otherwise a verifier can drift while the
bundle hash still passes.

Separate portable asset content identity from deployment location. Pin the
repository, revision, required file identities, and content manifest, then bind
the resolved root into the immutable attempt environment. Do not compare a
portable profile against a fixed manifest hash that embeds a site-specific
absolute path. A location-bound profile may retain such a hash when that exact
root is part of its explicit contract.

As a final one-shot check, subtract the prompt prose: reconstruct the launch
from the candidate checkout, site bootstrap, launch bundle, and single command.
Compare that environment and argv with the latest sustained-success runtime.
Any required operational delta that survives only in prose or ambient parent
state invalidates the bundle until it is encoded and behaviorally tested.
