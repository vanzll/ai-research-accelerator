# Review Gates

## Contents

1. Story gate
2. Evidence gate
3. Clarity gate
4. Visual and delivery gate
5. Reviewer red team
6. Clean-context technical review
7. Severity and readiness

## Story gate

- Can the contribution be stated in one sentence without a conjunction joining unrelated ideas?
- Is the paper driven by a real tension rather than a generic importance claim?
- Does every numbered Observation have evidence and force a later inference?
- Does every numbered Insight explain observations and imply a design principle?
- Is the method the minimal response to that principle?
- Does each section change the reader's understanding or support a central claim?
- Are secondary insights demoted when they compete with the main story?
- Are central mathematical claims stated as formal results rather than buried
  in prose, and does each result support a later Observation, Insight, or method
  step?
- Can every Observation and Insight box be understood in one glance, without
  protocol details or a paragraph of qualifications inside the box?

## Evidence gate

- Trace every number to a run, table, script, proof, or dataset.
- Verify every citation and sentence-level support relation.
- Distinguish training curves, best evaluation, final evaluation, and held-out evaluation.
- Check budget fairness: samples, rollouts, optimizer steps, GPU-hours, model size, and evaluation calls.
- Report uncertainty and seeds appropriate to the claim.
- Test plausible alternative explanations for central mechanism claims.
- Ensure ablations isolate one algorithmic axis.
- State whether evidence is correlational, diagnostic, causal, or theoretical.
- Keep hypotheses visibly separate from findings.
- For every Lemma, Proposition, Theorem, or Corollary, verify the assumptions,
  conclusion, proof, and scope independently. An empirical Observation cannot
  be used as proof of a mathematical claim.

## Clarity gate

Read once as a knowledgeable but non-specialist reviewer:

- Can each paragraph's main claim be underlined in one sentence?
- Is every Insight a truth-evaluable explanatory claim rather than an
  imperative, recommendation, method step, slogan, or summary?
- For every Insight, what evidence would weaken it, and what design principle
  follows from it?
- Does each symbol have one meaning and each concept one name?
- Are equations translated into words?
- Does every central formal result have a clear reader-facing explanation after
  its proof, without forcing a repetitive heading template?
- Are routine short formulas inline, and is every displayed equation important
  enough to interrupt the prose?
- Are conversational mechanism labels replaced by established technical terms,
  or explicitly quoted and defined when retained for intuition?
- Are sentence subjects concrete and close to their verbs?
- Can any sentence lose words without losing information?
- Are transitions logical relations rather than decorative phrases?
- Are words such as `novel`, `significant`, `robust`, `general`, and `optimal` justified?
- Does the prose avoid throat-clearing, inflated vocabulary, and repeated summary?

Then read as a domain expert and restore any precision lost through simplification.

## Visual and delivery gate

- Compile the exact active source, not an old draft.
- Inspect every page of the rendered PDF.
- Check figure text at final print size and use colorblind-safe encodings.
- Check table precision, units, arrows, bolding semantics, and captions.
- Verify all labels, references, citations, equations, appendices, and supplementary links.
- Verify Observation/Insight numbering and consistent callout colors.
- Verify callouts remain compact at final print size and point to nearby
  evidence rather than embedding full evidence summaries.
- Verify theorem numbering, labels, proof completeness, and appendix proof
  pointers for every formal result.
- Keep key-equation boxes white, square-cornered, thin-bordered, and free of decorative fill.
- Ensure callouts do not split awkwardly, overflow columns, or dominate the page.
- Verify current official venue rules, anonymity, page count, checklist, and artifact policy.

## Reviewer red team

Produce two independent readings.

### Contribution advocate

- What is the strongest defensible claim?
- What changes in the field if it is true?
- Which evidence is most convincing?
- Why is the contribution more than an engineering combination?

### Contribution skeptic

- Is the insight only a renamed observation?
- Could a simpler baseline explain the gain?
- Is the method derived from the insight or retrofitted to it?
- Is the closest prior work closer than the paper admits?
- Is one benchmark, seed, metric, or tuning choice carrying the claim?
- Which single missing experiment would most reduce confidence?
- Where does the paper overgeneralize?

Write the crux: the one issue on which acceptance most depends. Fix or explicitly bound it before low-severity prose work.

## Clean-context technical review

Run this gate after a material technical revision and before opening a paper PR or declaring a submission candidate. A material revision includes a new or changed central claim, theorem, proof, algorithm, mechanism, quantitative result, prior-work attribution, novelty statement, or literature comparison. Punctuation and purely local style edits do not require it.

Use a fresh subagent or isolated agent context. Provide only:

- the exact candidate section or compiled paper;
- the minimum notation and definitions needed to read it;
- the bibliography entries and primary sources cited by the reviewed claims;
- a neutral instruction to find errors rather than confirm correctness.

Do not provide the author conversation, discovery history, intended conclusion, previous reviews, suspected bug, proposed correction, acceptance strategy, or main agent's confidence. These leak the target answer and invalidate independence.

Require the reviewer to reconstruct each technical claim before judging it, then return findings as `Blocker`, `Major`, or `Minor`, each with an exact location, the failing statement, why it may be wrong, the assumption or source that decides it, and the smallest defensible correction. The review must check:

- factual and chronological accuracy;
- whether citations support the attached sentence rather than merely the topic;
- mathematical assumptions, conditioning, signs, constants, and quantifiers;
- whether the proof establishes the stated scope;
- whether an empirical diagnostic is being promoted into a causal claim;
- whether prior work is described charitably and novelty is bounded correctly;
- whether terminology changes the technical meaning.

Use the reviewer's native knowledge to surface contradictions and missing conditions, not as final authority. Verify every source-dependent or temporally unstable finding against the primary paper, official artifact, or experiment record. The writing agent adjudicates conflicts, applies accepted fixes, and reruns the isolated review after any material change. If the runtime cannot create a genuinely fresh context, record the gate as unavailable; an additional pass in the same context is not an independent technical review.

## Severity and readiness

- **Blocker:** fabricated/unverified evidence, invalid comparison, broken derivation, missing central experiment, unresolved closest-work overlap, or uncompilable submission.
- **Major:** unclear thesis, weak observation-to-insight link, unsupported mechanism, substantial scope overclaim, or confusing method.
- **Minor:** local wording, formatting, notation, or caption issue that does not change the scientific judgment.

A candidate is ready only when no blockers remain, major issues are resolved or explicitly accepted by the author, and the exact compiled artifact passes delivery checks.
