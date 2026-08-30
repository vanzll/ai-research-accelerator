# Skill Learning Decision Rubric

Use this rubric after an incident or correction. It is a gate against both
forgetting useful lessons and overfitting skills to anecdotes.

## 1. Establish confidence

Classify the proposed lesson:

- **Verified:** primary logs, tests, source inspection, or a successful repair
  establish the causal chain.
- **Supported:** multiple observations agree, but causality or the final repair
  is incomplete.
- **Speculative:** plausible explanation without decisive evidence.

Only verified lessons normally change normative skill rules. Supported lessons
may become a diagnostic question or project note when clearly labeled.
Speculation stays in the project record.

## 2. Test generality

A reusable lesson should answer yes to most of these:

- Could the same decision recur in another task or repository?
- Does it change what a future Agent should do or verify?
- Can it be stated without retaining incidental hostnames, IDs, or paths?
- Is the failure expensive, unsafe, silent, or otherwise worth preventing?
- Is the rule stable enough that likely exceptions can be stated coherently?

Expected network outages, transient third-party failures, and ordinary coding
mistakes without a reusable decision rule do not need a skill update.

## 3. Select the action

First require direct topic ownership. A candidate target skill qualifies only
if a future Agent would load it to make the failed decision and its documented
capability directly contains that workflow. Reject a target chosen merely
because the incident mentioned its tools, logs, processes, or an adjacent
concept. One incident should update one owning skill by default; multiple skill
updates require separate causal evidence for each.

- **Delete:** the existing rule is false, obsolete, duplicated, or harmful.
- **Replace:** the rule points in the right area but its invariant or boundary
  is wrong.
- **Narrow:** the rule is valid only under conditions it currently omits.
- **Extend:** the rule is correct but misses a proven adjacent failure mode.
- **Relocate:** the content is useful but lives in a skill that will not be
  loaded for the relevant decision.
- **Create:** no existing skill owns a distinct recurring capability.
- **No change:** evidence or generality is insufficient.

Prefer delete/replace/narrow over appending exceptions. Prefer updating an
existing skill over creating overlapping discovery entries.

## 4. Derive the invariant

Write four compact statements before editing:

1. **Observed failure:** what objectively happened?
2. **Root cause:** which assumption, control boundary, or implementation was
   wrong?
3. **General invariant:** what must be true in future tasks?
4. **Mechanical check:** what test or evidence can prove it?

Example:

```text
Failure: a healthy old worker dispatcher satisfied a new launch readiness gate.
Cause: readiness searched for any state file instead of the expected authority.
Invariant: readiness is bound to the canonical campaign and contract identity.
Check: compare campaign root/ID, contract hash, host, process generation,
       active attempt, nonce, and fencing epoch before accepting the worker.
```

The invariant belongs in a skill; the particular campaign names belong only in
the incident record or regression fixture.

## 5. Control change size

For one incident, prefer one to three high-value rule changes. Broader cleanup
is justified only when source review proves that several existing rules are
mutually inconsistent. Avoid large rewrites that erase still-valid context.

After several updates to the same skill, perform a consolidation pass:

- merge repeated rules;
- remove stale chronological narration;
- move conditional detail into references;
- keep the entrypoint concise and decision-oriented;
- confirm examples still represent current behavior.

## 6. Validate independently

At minimum:

- run the skill structure validator;
- run `diff --check`;
- inspect the complete changed passage in context;
- compare canonical and installed copies;
- run behavioral tests for changed scripts or validators.

For a risky or substantial skill rewrite, use an independent review when an
appropriate reviewer or subagent is available. Do not treat a keyword-presence
test as behavioral validation.
