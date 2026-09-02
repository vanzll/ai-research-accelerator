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

## Build the canonical runtime

1. Identify the latest accepted production run and its exact runtime commit,
   contract hash, evidence, and retrospective.
2. Compare its operational diff with the intended feature base. Classify each
   change as applicable, obsolete, scientific, uncertain, or site-specific.
3. Port or reimplement every applicable semantics-preserving fix on canonical
   main. Preserve attribution to the source attempt and commit. Do not merge a
   remote branch wholesale when it mixes science and operations.
4. Add a behavioral regression for the original failure. A source-string test
   is insufficient when the incident involved process lifecycle, rank
   divergence, asset identity, or parser behavior.
5. Run the incident regressions, frozen-path regressions, and any bounded real
   smoke that cannot be represented locally.
6. Update the production-runtime manifest and validate the new profile before
   writing its launch prompt.

## Manifest contract

Store a repository-owned JSON manifest, for example
`runtime/production_runtime_manifest.json`:

```json
{
  "schema_version": 1,
  "runtime_id": "video-policy-production-v4",
  "canonical_runtime_commit": "<40-char canonical commit>",
  "accepted_runtime": {
    "commit": "<40-char accepted run commit>",
    "evidence_paths": ["<attempt retrospective or acceptance evidence>"]
  },
  "fixes": [
    {
      "id": "transport-log-short-hostname",
      "status": "promoted",
      "promoted_commit": "<40-char canonical promotion commit>",
      "source_evidence_paths": ["<incident evidence>"],
      "regression_tests": ["tests/test_transport_attestation.py"],
      "required_for_profiles": ["*"]
    }
  ],
  "profiles": [
    {
      "id": "new-profile",
      "production_base_commit": "<same canonical runtime commit>",
      "required_fix_ids": ["transport-log-short-hostname"],
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

## Delegation gate

The coordinator's handoff names the validated manifest, profile, candidate
commit, validator output, regression report, and any remaining hardware-only
risk. Remote repair authority remains a fallback for genuinely new environment
failures. If the remote Agent rediscovers a manifest fix, treat that as a
release-gate defect and repair the canonical runtime before another profile is
launched.
