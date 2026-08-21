---
name: write-insightful-topconf-paper
description: Plan, discuss, draft, revise, and audit insight-driven papers for top ML/AI/vision/NLP conferences such as ICLR, ICML, NeurIPS, CVPR, and ACL. Use when Codex must shape a paper story from observations, derive a method from evidence, formalize mathematical claims as labeled results with proofs, map claims to experiments, write or revise LaTeX/Overleaf sections, improve its writing rules from author feedback, create numbered Observation/Insight/key-equation callouts, simplify academic prose, or perform a skeptical top-conference review. Also use for paper outlines, abstracts, introductions, motivation, methods, experiments, related work, limitations, rebuttals, and submission-readiness checks.
---

# Write Insightful Top-Conference Papers

## Governing priorities

Apply these priorities in order:

1. Preserve scientific truth. Never invent evidence, results, citations, chronology, mechanisms, or novelty.
2. Follow the user's locked framing, terminology, scope, and task mode. If the user asks to discuss logic, do not start drafting.
3. Make the paper insightful. Let observations expose a tension, let an insight resolve it, and let the method appear as the minimal response.
4. Make the paper easy to understand. Prefer the simplest accurate word and the shortest complete explanation.
5. Satisfy the current official venue rules. Verify changing requirements rather than recalling them from memory.

Treat prose as the final encoding of a scientific argument, not as the starting point.

Use citation, literature-search, PDF-inspection, and scientific-diagram skills when installed. They are optional integrations: without them, use authoritative local sources or report the corresponding verification gap.

## Route the request

Choose the smallest route that satisfies the user:

- **Logic discussion:** reason one link at a time; keep answers concise; do not mutate paper files.
- **Story or outline:** create the story contract and argument chain before prose.
- **Section drafting:** establish the section's reader question, claim, evidence, and bridge before writing.
- **Revision:** preserve meaning unless the user authorizes a scientific change; report any changed claim scope.
- **Review:** lead with rejection risks, unsupported claims, missing evidence, and confusing logic.
- **Submission:** verify the exact compiled candidate, references, figures, anonymity, page limits, and supplementary package.

For full-paper work, read all three references:

- [story-architecture.md](references/story-architecture.md)
- [section-playbook.md](references/section-playbook.md)
- [review-gates.md](references/review-gates.md)

For a bounded request, load only the relevant reference.

## Learn from author feedback

Treat explicit author criticism as an input to both the current artifact and the
reusable writing process. Do not merely repair the quoted sentence.

1. Identify the exact failure mode and the smallest counterexample supplied by
   the author.
2. Separate a paper-specific preference from a reusable writing rule. Preserve
   local preferences in the project record; add only generalizable rules to the
   skill.
3. Express each reusable lesson as an operational test with a bad case and a
   passing condition. Update a deterministic audit only when the property can be
   checked without pretending that a semantic judgment is mechanical.
4. Re-audit neighboring instances of the same construct in the current paper,
   revise them consistently, and validate both the skill and the artifact.
5. Report the rule learned, the current locations changed, and any judgment that
   still requires the author.

Do not preserve feedback as a chronological changelog inside the skill. Fold it
into the governing rule at the narrowest appropriate location. Do not
overgeneralize one wording preference into a scientific convention.

## Maintain synchronized Chinese writing surfaces

When the author requests a Chinese editing surface, use the format they prefer.
For high-frequency semantic iteration, prefer a readable Markdown file such as
`main_zh.md`; use a compilable XeLaTeX mirror only when the author requests one
or needs page-level Chinese rendering. Do not overwrite exploratory notes such
as `draft.md` or `paper_draft.md` unless the author explicitly selects them.

When the project contains both a Chinese Markdown guide and a Chinese TeX
manuscript, treat them as three distinct surfaces:

1. **Chinese Markdown guide:** author instructions, high-level semantics,
   stable paragraph jobs, and unresolved comments.
2. **Chinese TeX manuscript:** the author's readable, compilable iteration
   draft containing polished Chinese paper prose rather than agent
   instructions.
3. **English TeX manuscript:** the final submission artifact.

Do not collapse these roles. If the author says they iterate through Chinese
TeX, every material prose revision must update the Chinese and English TeX in
the same turn while leaving the Markdown guide unchanged unless explicitly
asked. Preserve matching section structure, labels, equations, formal-result
scope, callouts, figures, and citations across both TeX manuscripts. Compile
and inspect both artifacts before closing. The Chinese TeX may use natural
Chinese exposition rather than sentence-level translation, but it must not lag
behind the scientific content of the English submission.

- Treat the English LaTeX as the submission artifact and the author's selected
  Chinese surface as the active control document. Codex may initialize it, but
  after the author begins editing it, regard it as read-only unless the author
  explicitly asks to modify, synchronize, or clean up that Chinese draft. A
  separate Markdown guide remains read-only when the author iterates in Chinese
  TeX.
- In a Markdown semantic draft, mirror the paper's section hierarchy and assign
  every paragraph or formal block a stable ID. Prefix it with one short visible
  planning line, for example `[S2-P3 | Core: explain why conditional branch
  balance is not guaranteed by global reward balance.]`. This line states the
  paragraph's single high-level job; it must not become a second paragraph,
  contain detailed evidence, or accumulate multiple claims.
- If the author adopts delimiters such as `{...}` or `「...」` as an instruction
  convention, treat delimited text outside math, code, citations, and other
  formal syntax as author-to-agent comments rather than manuscript edits. Never
  translate or synchronize these comments into the English paper. Execute them
  against the English submission artifact while preserving the author's comment
  in Markdown unless the author explicitly requests cleanup. LaTeX braces inside
  `$...$`, `$$...$$`, fenced code, or raw LaTeX retain their ordinary syntactic
  meaning.
- Semantic equivalence means identical claims, evidence scope, caveats,
  Observation/Insight roles, formal results, equations, citations, and method
  behavior. It does not require literal sentence-by-sentence translation.
- Treat the Chinese control document as a semantic specification, not a prose
  template. Unless the author explicitly locks wording, freely paraphrase,
  merge, reorder, or omit its explanatory scaffolding when the English can
  express the same argument more directly. Chinese paragraph boundaries do not
  constrain English paragraph boundaries.
- Before synchronizing a section, extract an **author-lock checklist** from the
  Chinese control document and the latest explicit feedback. It must list: the
  locked section/subsection titles or conceptual framing; every mandatory
  concept, algorithm step, advantage, caveat, figure, and formal result; the
  requested level of detail; and any instruction to follow a primary source.
  These are semantic constraints, not explanatory scaffolding. Compression may
  shorten their wording but may not delete, demote, or silently rename them.
- Treat requests such as `write this part in more detail`, `explain the full
  algorithm`, or `closely follow the original paper` as minimum-coverage
  requirements. A concise revision passes only if an expert reader can recover
  every requested stage and its role. Page pressure is not authority to omit a
  locked item; surface the budget conflict or compress lower-priority prose.
- Preserve an author-specified heading verbatim when it is presented as the
  desired English heading. When only its meaning is specified, preserve the
  same technical subject and scope. Do not replace a method-specific heading
  with a more generic label merely for stylistic uniformity.
- Run an intent-to-prose compression test during synchronization: preserve the
  claim, logical dependency, evidence boundary, and requested emphasis, then
  use the fewest sentences needed for a first-pass expert reader to recover
  them. A passing English paragraph may be substantially shorter than its
  Chinese source; a sentence-level calque is a failure even when technically
  accurate.
- Preserve equations and LaTeX labels verbatim when the Chinese draft is LaTeX.
  In Markdown, preserve the equation content and map each formal block to the
  English label through its stable ID or an adjacent `SYNC` comment.
- When the author says they have rewritten or annotated the Chinese Markdown and
  asks Codex to `refine`, inspect the Markdown but edit the English LaTeX. Do not
  rewrite the author's Chinese prose. Interpret ordinary Chinese edits as the
  desired semantics and delimited comments as instructions for how to realize
  those semantics in polished academic English.
- When the author edits Chinese, inspect its diff first and treat the changed
  meaning as authoritative unless it conflicts with verified evidence or a
  mathematical result. Surface such conflicts instead of silently weakening or
  reversing the edit.
- Translate the final meaning into natural academic English; do not retain
  Chinese syntax merely to achieve literal correspondence. If mathematical or
  evidential review requires changing the author's claim, report the conflict
  instead of silently correcting the Chinese control document.
- For a XeLaTeX mirror, compile after every material edit. Prefer the project's
  existing Chinese setup; otherwise use `fontspec` with an available CJK font.
  When both Chinese and English TeX exist, compilation success of only one is
  insufficient.
- For a Markdown semantic draft, compile the synchronized English LaTeX after
  every material transfer and manually audit stable-ID coverage, claim scope,
  equations, citations, and callout roles. If the project has a deterministic
  sync audit, run it as well.
- The stable-ID audit must include instruction resolution, not just topic
  overlap. For every `{...}` or `「...」` instruction, record internally where
  it was satisfied in the English artifact or why it remains blocked. Before
  closing, compare the author-lock checklist against the rendered section and
  report any deliberately unresolved item.

## Present prior methods faithfully before critique

When a preliminary or motivation subsection introduces a prior method that the
paper later analyzes, separate faithful exposition from the paper's new
interpretation.

- If the author asks to follow the original work, re-read the primary paper and
  verify the method sequence, notation, objective, update schedule, and claimed
  benefits. Do not reconstruct the prior method only from discussion notes or
  the new paper's derived notation.
- A method-specific preliminary should normally let the reader recover:
  `sampling distribution -> supervision or preference construction -> state
  construction -> loss/objective -> optimizer/reference update -> claimed
  computational advantage`. Include only stages that actually exist in the
  cited method, but do not collapse this sequence into a bare equation when the
  author requested the complete algorithmic picture.
- Use the prior work's terminology for its own constructs before introducing
  new symbols needed by the analysis. Clearly mark which identities,
  decompositions, or failure explanations are contributed by the current
  paper rather than claimed by the cited work.
- Keep analysis-only notation out of the preliminary unless it is required to
  state the prior method. Introduce derived population fields, diagnostic
  quantities, and reinterpretations at their first analytical use. A concise
  preliminary should spend each sentence on an original algorithm stage, a
  dependency needed by the next subsection, or a verified claimed advantage.
- A passing preliminary is charitable and self-contained: a reader unfamiliar
  with the cited method should understand how one iteration works before being
  asked to accept its limitation. Concision should remove repetition, not
  prerequisite steps.

## Enforce a section contract before prose

For motivation, introduction, method, or experiment sections, write a compact
section contract before editing prose:

```text
Reader question:
Formal result(s), if any:
Observation callout(s):
Insight callout(s):
Key equation callout(s), if any:
Evidence or derivation behind each callout:
Inline equations versus displayed equations:
Formal terminology to use; informal terminology to avoid:
Bridge to the next section:
```

If the user has already identified a statement as a central `Observation` or
`Insight`, preserve that role unless scientific review shows it is unsupported.
In LaTeX papers, encode each supported central statement with the corresponding
callout environment. Do not silently demote it to an ordinary paragraph or
bold lead-in. If it is unsupported, stop and report the evidence gap instead of
boxing it as fact.

## Build the story before drafting

Inventory authoritative materials first: active draft, project plan, notes, code, experiment ledger, W&B runs, tables, figures, bibliography, and venue template. Distinguish verified evidence from hypotheses and planned evidence.

Create a compact story contract:

```text
Problem:
Accepted belief or current practice:
Observation(s):
Tension or failed explanation:
Core insight:
Design principle:
Method in one sentence:
Key prediction(s):
Decisive evidence:
Contribution boundary:
Claims to avoid:
```

Require one primary thesis. Secondary contributions must support it rather than create parallel stories.

## Derive the method from evidence

Use this chain whenever the evidence supports it:

```text
Observation -> Tension -> Insight -> Design principle -> Method -> Prediction -> Experiment
```

- An **Observation** is a reproducible empirical or mathematical fact, with named evidence.
- A **Tension** states why the observation is not explained by the prevailing account.
- An **Insight** is the smallest new, falsifiable claim that explains the
  tension. It must be a declarative proposition that can be true or false.
- A **Design principle** states what any solution must do if the insight is correct.
- The **Method** should be the simplest implementation of that principle.
- A **Prediction** must be falsifiable and distinguish the insight from alternatives.
- An **Experiment** tests the prediction, not merely the final benchmark score.

Make the idea feel inevitable through logic, not rhetoric. It is acceptable to reorganize the exposition into its clearest logical order. Do not claim that this was the historical discovery order unless records establish that fact.

Apply the **claim test** before labeling any sentence as an Insight:

- It should remain grammatical after `We argue that ...` or `Our evidence
  suggests that ...`.
- A skeptical reader should be able to name evidence that would weaken or
  falsify it.
- It must state a relation, mechanism, boundary, or changed explanation, not an
  action for the method to perform.

An imperative such as `Aggregate endpoint evidence before the Jacobian` or
`Apply restoration after the first update` is a design principle, not an
Insight. First state the explanatory claim; derive the prescription afterward.

## Maintain claim-evidence discipline

Before long-form prose, map central claims to evidence:

| ID | Claim | Evidence | Status | Scope limit | Paper location |
|---|---|---|---|---|---|
| C1 | Narrow, testable statement | Run/table/proof/citation | verified/planned/missing | What it does not show | Section/figure |

Rules:

- Every experiment must support or challenge a named claim.
- Every exact number must trace to an artifact.
- Every citation must be verified and support the attached sentence, not just the topic.
- Separate observed fact, interpretation, mechanism hypothesis, and causal claim.
- Treat negative and mixed results as scope information; never hide them.
- If evidence is missing, weaken the claim or mark the gap. Do not fill it with fluent prose.

## Formalize mathematical claims

Before drafting equations, classify every central mathematical claim:

- use a **Definition** to introduce a new object;
- use a **Lemma** for a focused identity or technical fact used later;
- use a **Proposition** for a substantive property of an objective or method;
- reserve **Theorem** for a main result with meaningful scope;
- use a **Corollary** only for an immediate consequence of a preceding result.

If a mathematical claim changes the paper's argument, do not bury it in prose or
present only a sequence of aligned equations. State it in a numbered formal
environment with:

1. the conditioning, assumptions, and symbol definitions needed to make it true;
2. one precise conclusion;
3. a `\label{...}`;
4. a proof immediately afterward, or an explicit pointer to a complete appendix proof.
5. a short reader-facing explanation after the proof for every result central
   to the paper story.

Use `amsthm` or the venue's compatible theorem machinery. Keep the main-text
proof only as detailed as needed to establish credibility and support the next
logical step. Prefer a short complete proof when it fits. Otherwise provide a
precise proof sketch, move algebra, technical regularity conditions, and routine
steps to the appendix, and cite the exact appendix location. Never label an
empirical pattern, mechanism hypothesis, or approximate diagnostic as a theorem.

Keep the roles separate:

```text
Lemma/Proposition/Theorem = what follows mathematically.
Observation                = what the evidence shows.
Insight                    = what changes in our understanding.
Design principle           = what a method should do as a consequence.
```

An Observation box cannot substitute for a proof. An Insight box cannot claim
more than the formal result and evidence jointly support. Every Insight box
must contain a declarative claim. Never place an imperative instruction, method
step, design recommendation, slogan, or section summary in an Insight box.

After each story-critical result, explain in one or two plain sentences what it
changes in the reader's mental model. Integrate this explanation naturally into
the prose; do not require an `Intuition.` heading. Valid forms include
`Intuitively, ...`, `The result has a direct interpretation: ...`, or a seamless
explanation with no explicit cue. Do not merely restate the equation symbol by
symbol. Avoid the unidiomatic phrase `Intuitively understanding`.

## Design notation for first-pass comprehension

Before drafting a formula-heavy section, create an internal notation contract
with one row per symbol: meaning, mathematical type or shape, conditioning and
suppressed arguments, frozen/current status, first definition, and nearby
symbols it could be confused with. The reader should never need to infer these
properties from an equation.

- Define an object before its first equation-level use. When dependencies are
  suppressed, state the full form once, such as
  `$q_t=q(x_t,t,c)$`, before using the shorter notation.
- Encode one semantic distinction per visual convention. For example, a bar may
  consistently denote a conditional population mean, while a descriptive
  subscript may identify a rollout field. Do not stack unexplained letter
  superscripts to encode source, process, time, and optimization status at once.
- Prefer semantic names for story-critical objects and short names for local
  algebra. A local abbreviation must be introduced immediately before the
  derivation, used within a small scope, and must not collide with a global
  parameter, distribution index, reward, timestep, or standard operator.
- Do not reuse one symbol for different concepts in neighboring sections. In
  particular, audit tilt parameters, loss coefficients, residuals, advantages,
  and probability ratios for collisions.
- Distinguish random sample targets, learned fields, population-optimal fields,
  and actual sampler fields explicitly. Similar vector spaces do not make these
  objects interchangeable.
- Use a new symbol only when it reduces total reading cost. If an object appears
  once or twice, spelling out the expression or naming it in prose is often
  clearer than adding notation.
- Immediately after each central display, state in words what each side
  represents and which quantity the equation changes. Explain the relation, not
  a symbol-by-symbol transcription.

Before a paper PR, give a fresh clean-context subagent only the candidate
artifact and ask it to reconstruct the notation contract without seeing the
author's intended glossary. Treat every missing, ambiguous, overloaded, or
incorrectly reconstructed symbol as a clarity defect. Revise until a first-time
expert can identify for every central equation: what is random, what is learned,
what is conditioned on, what is frozen, and what space the equality inhabits.
This notation audit complements, rather than replaces, the technical review.

## Control equation density

Classify each formula before typesetting it:

- **Inline:** short definitions, substitutions, proportionalities, and formulas
  that are read once and not referenced later.
- **Displayed:** central objectives, multi-step derivations, formal-result
  conclusions, or formulas referenced later.
- **Key-equation callout:** only the one or two reusable equations the reader
  should remember after leaving the section.

Do not give a short routine formula its own numbered line merely because it is
mathematical. If a displayed equation is not central, not needed for visual
derivation, and never referenced later, make it inline. After drafting, scan the
rendered page: a page dominated by isolated equations usually needs
consolidation, not smaller type.

## Write for fast comprehension

- Use the simplest accurate word. Prefer `use` over `utilize`, `show` over `demonstrate` when no stronger meaning is needed, and concrete verbs over nominalizations.
- Give each sentence one main job. Keep the subject close to its verb.
- Put the claim early, then evidence or reasoning, then its implication.
- Use one stable term per technical concept. Do not rotate synonyms for variety.
- Prefer established technical terms over conversational metaphors. For
  example, write `positive/negative fitting`, `reward-improving update`,
  `restoration`, and `orthogonal function movement` rather than `push/pull`,
  `pushing away`, `the signal gets swallowed`, or `sideways movement`.
- Use an informal metaphor only when it materially improves intuition. Put it
  in quotation marks, define its technical meaning immediately, and do not use
  it as the name of a theorem, subsection, variable, or primary mechanism.
- Define symbols and specialized terms at first use; immediately explain important formulas in words.
- Remove throat-clearing such as "In this section, we discuss" and empty emphasis such as "It is worth noting."
- Avoid inflated adjectives and unsupported words such as `novel`, `significant`, `robust`, `comprehensive`, and `fundamental` unless the paper establishes the intended meaning.
- Prefer explicit logical relations over decorative transitions.
- Keep necessary technical detail, but remove prose that does not change the reader's model.
- Do not explain the same mechanism in the setup, formal-result interpretation,
  callout, and transition. Assign the full explanation to one location; elsewhere
  use only the premise or consequence needed for local flow.
- After drafting, perform a compression pass on every paragraph: delete repeated
  premises, merge sentences with the same subject, and remove any sentence whose
  deletion preserves the claim, evidence scope, and transition.

Do not make every paragraph follow an obvious template. Vary length naturally while preserving argument flow.

## Use visual callouts selectively, with a hard gate

Use [topconf-callouts.sty](assets/topconf-callouts.sty) when the paper uses LaTeX. Copy it into the paper source tree and load it in the preamble:

```latex
\usepackage{topconf-callouts}
```

Available environments:

```latex
\begin{observation}[Short descriptive title]\label{obs:example}
Verified empirical or mathematical fact, including the evidence pointer.
\end{observation}

\begin{insight}[Short descriptive title]\label{ins:example}
Interpretation that resolves a tension and motivates a design principle.
\end{insight}

\begin{keyequation}
\begin{equation}
  y = f(x).
\end{equation}
\end{keyequation}
```

The style automatically numbers Observations and Insights globally. Use:

- orange Observation boxes only for facts central to the argument;
- blue Insight boxes only for genuinely new explanatory statements;
- white, square-corner equation boxes only for equations readers must retain.

Do not box routine definitions, implementation details, ordinary results, or multiple consecutive paragraphs. Normally use at most a few callouts in the main paper.

Callouts are memory anchors, not miniature paragraphs:

- keep each box to one sentence whenever possible and never more than two;
- target at most 45 prose words, excluding the title and citation commands;
- state only the highest-level fact or explanation in the box;
- move numbers, protocol, caveats, and derivation into nearby prose, a figure,
  or a table, and point to that evidence from the box;
- keep titles descriptive and under roughly ten words.

For an insight-driven section, `selectively` means selecting the few statements
that carry the argument; it does not permit omitting all callouts after the
story contract identifies central Observations or Insights. Before editing:

1. name every planned callout and classify it as fact, interpretation, or key equation;
2. place explanatory prose before and after each box;
3. keep evidence and scope limits inside an Observation box;
4. keep the new explanation and resulting design implication inside an Insight box;
5. never substitute `\textbf{Observation ...}` or `\paragraph{Insight ...}` for the environments.

For LaTeX delivery, fail the callout gate when any of these holds:

- the section contract names a central Observation but the source has no matching `observation` environment;
- it names a central Insight but the source has no matching `insight` environment;
- an Observation lacks a run, table, proof, or citation pointer;
- an Insight merely repeats its preceding Observation or does not imply a design consequence;
- boxes appear consecutively without prose that derives or interprets them.
- a callout exceeds two sentences or approximately 45 prose words without a
  compelling reason;

## Draft in two passes

1. Draft the evidence-bearing core first: notation, method, experimental protocol, results, and limitations.
2. Rebuild framing from the stabilized evidence: motivation, introduction, related work positioning, abstract, title, and conclusion.

For each section, state the reader question before drafting. For each paragraph, know its function, narrow claim, authorized evidence, inference limit, and bridge to the next paragraph.

## Review as a skeptical committee

Run four distinct passes:

1. **Story:** Is there one thesis? Does each section advance it? Does the method follow from the insight?
2. **Evidence:** Are claims supported, scoped, reproducible, and fairly compared?
3. **Clarity:** Can an expert understand each paragraph on one read? Are terms and notation stable?
4. **Delivery:** Do LaTeX, figures, tables, references, labels, anonymity, and venue constraints hold in the exact candidate?

Then perform two opposing reviews:

- **Advocate:** state the strongest defensible contribution and why it matters.
- **Skeptic:** identify the simplest alternative explanation, closest prior work, missing decisive experiment, and likely rejection reason.

Resolve the skeptic's strongest valid objection before polishing minor language. Read [review-gates.md](references/review-gates.md) for the full checklist.

## Require a clean-context technical review

After any material technical revision, and before a paper PR or submission candidate, use a fresh subagent when the runtime supports one. Give it only the candidate artifact, minimal symbol definitions, and cited primary sources; withhold author intent, prior debate, suspected flaws, proposed fixes, and the desired verdict. Ask it to reconstruct and audit factual claims, assumptions, derivations, attribution, terminology, and claim scope. Its native knowledge is a fault detector, not evidence: verify source-specific or unstable facts against primary sources. The writing agent must adjudicate findings and rerun the review after material fixes. If no isolated reviewer is available, report that this gate was not run rather than simulating independence in the current context. Follow the clean-context protocol in [review-gates.md](references/review-gates.md).

## Verify the artifact

For LaTeX work:

1. Run `scripts/audit_tex.py` on the main source or paper directory. For an
   insight-driven section with planned callouts, pass
   `--require-observation N --require-insight M` using the section contract's
   minimum counts. If the contract contains mathematical results, also pass
   `--require-formal-result K`; when those results have local proofs, pass
   `--require-proof K` as well. Use `--check-formal-explanation` only as a
   heuristic check; manually verify that each central result has a natural
   reader-facing explanation and that every abbreviated proof points to the
   exact appendix location.
2. Compile the exact paper if the environment permits.
3. Render and inspect the PDF for overflow, broken references, box styling, figure readability, and page count.
4. Re-run affected checks after every material edit.

Never call a paper submission-ready when evidence, citations, experiments, or build checks remain unresolved. Report what changed, what was verified, and what remains uncertain.
