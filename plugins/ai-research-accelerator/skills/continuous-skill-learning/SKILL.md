---
name: continuous-skill-learning
description: Distill verified lessons from user corrections, avoidable retries, reviews, incidents, and surprising task outcomes into concise reusable Codex skills. Use automatically after evidence exposes a wrong, missing, stale, duplicated, or overly specific skill rule, or when a genuinely reusable workflow has no existing skill. Correct and prune existing skills before creating new ones.
---

# Continuous Skill Learning

Persist learning by improving instructions, checks, tests, and canonical skill
sources. This is not model-weight training and does not justify changing user
intent, scientific semantics, permissions, or unrelated code.

## Trigger automatically

Run a learning audit after the primary task is stable when any of these occurs:

- the user corrects the Agent or explicitly identifies a mistake;
- an avoidable Agent, launcher, workflow, or validation defect causes a retry;
- primary evidence contradicts a skill rule or an earlier conclusion;
- a review or test exposes a reusable missing guard;
- a recovery method is validated and would prevent a similar future failure;
- multiple project notes reveal the same recurring decision problem.

Do not wait for the user to request reflection again. Do not interrupt urgent
recovery merely to edit a skill: first contain or fix the incident, preserve
evidence, then perform the audit before final handoff. A valid audit may decide
that no skill change is warranted.

## Consume delegated-run retrospectives

When analyzing a W&B run, reconciling its ledger, or resuming remote training,
read the attempt retrospective named by the run contract before the learning
audit. Treat it as an index, not proof; verify claims against logs, code,
commits, tests, and W&B. Mark `Reviewed` after triage (`no reusable change` is
valid), and mark `Absorbed` only after the canonical skill is corrected,
synchronized, validated, and its commit recorded.

Be critical in both directions: question whether the existing workflow or skill
guidance contributed to the incident, and challenge every new retrospective
claim before organically integrating only its evidence-backed portion; neither
defend the status quo by default nor blindly accumulate new rules.

Do not mark a remote hypothesis absorbed merely because its repair coincided
with a successful retry. Leave uncertain lessons pending and preserve the
evidence path for later runs.

## Require evidence before learning

Record the incident in the current project's established progress document with
the observed behavior, evidence paths, root cause, impact, successful repair,
and remaining uncertainty. Never promote speculation, a single unexplained
correlation, an external outage, or a project-specific path into a general
rule.

Read [decision-rubric.md](references/decision-rubric.md) when deciding whether
to update, delete, relocate, or create a skill rule. Resolve conflicts against
primary evidence and current authoritative documentation where relevant.

## Prefer correction over accumulation

Search the available skills and their canonical sources before editing.

Apply a strict topic-ownership gate before selecting a target skill. Its core
capability and trigger must directly own the failed decision or workflow; the
incident must expose a defect in that skill's guidance or implementation.
Incidental co-occurrence, broad technical relevance, or a lesson that could be
useful to readers of an adjacent skill is insufficient. Do not update several
skills from one incident unless primary evidence shows that each skill
independently contributed a wrong or missing decision. Otherwise keep the
lesson in the project record or update only the directly responsible skill.

1. **Delete or replace incorrect guidance.** Do not append a contradictory
   exception while leaving a false rule active.
2. **Update the narrowest existing skill.** Put the invariant where an Agent
   making that decision will load it. Consolidate duplicates into one source of
   truth and keep references discoverable from `SKILL.md`.
3. **Create a new skill only for a distinct reusable capability.** A new skill
   needs a discriminating trigger and enough recurring workflow to justify
   separate discovery. One incident, one cluster, or one repository is usually
   not a capability.
4. **Keep project facts in project records.** Generalize away hostnames,
   usernames, attempt IDs, temporary paths, and one-off commands unless the
   skill is intentionally environment-specific.

Write the smallest rule that changes future behavior. Preserve useful existing
content and remove stale, redundant, overfitted, or disproven text. Skill
quality is measured by decision quality, not length.

## Mechanize repeatable prevention

When a property is objectively checkable and likely to recur, add or improve a
validator, preflight, schema check, or regression test instead of relying only
on prose. Tests should exercise behavior or invariants, not merely assert that
a sentence exists. Do not build automation for a low-confidence or one-off
lesson.

For code-backed skills, review both instructions and their scripts: correcting
documentation while leaving a conflicting implementation is incomplete.

## Synchronize the canonical source

Identify the canonical editable source before changing an installed skill.
Prefer this sequence:

1. update the version-controlled plugin or skill source;
2. update any relevant reference, script, test, and progress record;
3. synchronize the installed runtime copy;
4. run the skill validator plus relevant behavioral tests and `diff --check`;
5. commit only the intended files, and push only when the repository and current
   authorization already permit it.

If the source mapping is unknown, do not guess or overwrite an unrelated
repository. Update the safely identifiable copy, record the pending sync, and
report the limitation. Never revert unrelated dirty worktree changes.

## Preserve authority and secrets

Learning does not expand permissions. Do not use it to change algorithm or
experiment semantics, enable new services, access new credentials, or broaden
the original task. Ask before encoding a disputed policy or a change whose
correctness depends on user preference rather than evidence.

Never record credentials, tokens, private payloads, or secret values in skills,
examples, tests, commits, progress records, or learning summaries. Replace
environment-specific values with roles, schemas, and redacted placeholders.

## Finish the audit

Before reporting completion:

- confirm the new guidance does not conflict with neighboring skills;
- verify installed and canonical copies match when both are maintained;
- run structural validation and relevant tests;
- record what was corrected, removed, added, and why;
- state explicitly when no reusable lesson met the evidence threshold.

Keep the user-facing summary short. The durable value belongs in the corrected
skill and its tests, not in a long narrative reflection.
