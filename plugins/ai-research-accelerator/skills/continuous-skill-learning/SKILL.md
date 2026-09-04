---
name: continuous-skill-learning
description: Carry verified lessons from delegated runs and incidents into task context and canonical code, using the latest validated successful commit as the next implementation baseline. Update skills only when evidence exposes a reusable workflow defect.
---

# Continuous Skill Learning

Use this skill to preserve verified learning across Agents and sessions. It is
not model training, and it must not turn every correction into a new process.

## Run the learning loop when evidence warrants it

After the primary task is stable, perform a short learning audit when a user
correction, avoidable retry, real runtime incident, or successful repair exposes
a reusable decision problem. The normal result is a verified code baseline and
updated incident watermark, not a skill edit. A valid audit may conclude that no
change is needed.

## Use one durable interaction medium

For repository work, keep one discoverable incident index under the repository
root, normally `踩坑记录/`. Large logs may remain on shared storage, but the root
record links them. This index is the asynchronous conversation between the
coding Agent that supplied a commit and the remote Goal Agent that exercised it.

A remote code-repair record should contain:

- supplied full commit and secret-free launch command;
- observed failure and primary evidence;
- successful full commit and command, when different;
- relevant Git delta or changed paths, tests, science impact, and uncertainty.

Do not require fields that add no decision value for the incident. Never store
credentials or private payloads.

## Verify before absorbing

Treat remote prose as an index, not proof. Check material claims against the
actual commit diff and the smallest relevant logs, tests, W&B history, or
runtime evidence. Distinguish observation, hypothesis, candidate repair, and
validated cause. A successful combined retry does not prove every included
change was necessary.

Before a related implementation or prompt, read only incident records newer
than the last reviewed watermark and bring their relevant evidence into the
current task context. Extract the supplied and successful commits and commands,
verify the material diff, then use the latest validated successful commit, or a
canonical descendant proven to contain its applicable repairs, as the baseline
for the new work. Apply only the newly declared scientific delta on top of that
baseline. Promote a missing applicable operational repair before asking another
remote Agent to rediscover it; scientific or uncertain changes require explicit
approval. Advance the watermark after this triage, including a valid no-change
result.

Record two independent outcomes when relevant:

- `Reviewed`: evidence was triaged, including a valid no-change result;
- `Absorbed`: the verified instruction or code repair is present in the
  canonical source and its focused validation passed.

A known applicable repair that remains outside canonical code blocks a claim
that the related executable prompt is ready. It does not require inventing a
production certificate, bundle, or manifest when the repository does not
already use one.

## Change the narrowest owner

Absorbing an incident does not itself justify editing a skill. Be critical of
both the existing workflow and the retrospective. Change only the skill whose
core responsibility contains a demonstrated reusable decision defect; keep
project facts and code lineage in the repository incident record. Replace wrong
guidance instead of appending contradictions, and create a new skill only for a
genuinely separate recurring capability.

Prefer a concise decision rule over instructions for ordinary coding. Add a
validator or regression only when the property is objective, recurring, and
worth mechanizing; use the smallest check that would have prevented the retry.

## Synchronize only when a skill changes

Update the version-controlled canonical skill source first, then synchronize
maintained installed copies. Run structural validation, relevant focused tests,
and `diff --check`. Preserve unrelated worktree changes and existing authority
boundaries. Summarize what changed and why; the durable value belongs in the
corrected skill, canonical code, and incident record rather than a long chat
retrospective.
