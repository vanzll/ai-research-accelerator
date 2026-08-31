---
name: edit-overleaf-with-edge
description: Edit an open Overleaf paper through the user's Edge browser extension, process author review comments and tracked revisions, polish or translate manuscript text, compile and inspect the rendered PDF, upload paper assets, and preserve completed edit batches with timestamped Overleaf History labels. Use when the user asks Codex to modify, polish, review, compile, or visually refine an Overleaf project in Edge.
---

# Edit Overleaf With Edge

Use the live, signed-in Overleaf tab in Microsoft Edge. Read and follow
`browser:control-in-app-browser` before browser interaction, and select Edge
explicitly. Do not substitute another browser.

## Non-negotiable invariants

- Claim the already-open project tab by its current title and URL. Do not guess a
  tab ID or open a duplicate project when the intended tab exists.
- Confirm the project, target file, scope, and current editing mode before
  changing anything.
- Keep exactly one live-project writer. Subagents may analyze frozen source
  snapshots, but must never edit the same Overleaf project, resolve comments,
  compile, or create History labels.
- If Git, GitHub, or another synchronized copy is currently authoritative,
  surface the conflict instead of silently creating a divergent Overleaf state.
- Preserve unrelated author and collaborator work. Never use project-wide
  **Accept all** when unrelated changes may exist.
- Leave the project in **Reviewing** mode with the latest compiled PDF visible.

## Choose the workflow

- **Process author review:** the user says `处理我的 review`, `process my
  review`, or equivalent. Process all pending user-authored tracked changes and
  unresolved comments unless a narrower scope is named.
- **Direct text edit:** edit one requested logical batch, compile once, and add
  one final History label.
- **Visual or asset edit:** upload or modify figures/tables/layout, compile, and
  inspect the affected PDF pages until visually correct. Label only the accepted
  final state, not intermediate attempts.

## Process author review

For an ordinary single-file, text-focused batch, target roughly 5--10 minutes.
Use one inventory, one edit batch, one compile, and one finalization pass.

### 1. Inventory once

1. Open the Review panel and expand `More comments` until it no longer appears.
2. Record the final counts of in-scope tracked changes and unresolved comments,
   including author and referenced location. Initially visible cards are not a
   complete inventory.
3. Capture the relevant live source and enough local context once. If the Review
   panel does not expose a complete diff after one attempt, use the live source
   rather than retrying the same UI.
4. Classify every item as direct acceptance, conservative copy-editing,
   Chinese-to-English translation, or comment-driven local revision.
5. Freeze the batch. Do not reread this skill, rescan Git, reopen unchanged UI,
   or repeat discovery unless evidence reveals a real scope or source conflict.

### 2. Preserve the starting point

Before accepting or rewriting anything, create exactly one label:

```text
Codex YYYY-MM-DD HH:MM TZ | before processing author review
```

This is the rollback point and preserves the author's reviewable draft.

### 3. Apply one coherent batch

- Treat the author's claims, notation, citations, argument order, emphasis, and
  characteristic phrasing as locked unless a comment requests substantive
  rewriting.
- Fix only clear grammar, punctuation, capitalization, agreement, and LaTeX
  mechanics. Make the smallest rephrasing needed for correctness; do not polish
  merely by changing style.
- Translate Chinese into natural academic English while preserving meaning.
- Treat each comment as a local instruction for its referenced text, equation,
  figure, table, or section. It does not authorize unrelated edits.
- Do not silently alter uncertain mathematics, evidence, or scientific claims.
  Leave ambiguous items pending and ask the author.
- Prefer targeted replacements. Do not replace or reselect the entire manuscript
  for a citation, cross-reference, notation fix, or other local correction.
- Apply all compatible changes before compiling. Accept only in-scope tracked
  changes; tracked deletions remain deletions unless a related comment says
  otherwise.
- Use `write-insightful-topconf-paper` only when the requested change is
  substantive paper writing, not for ordinary grammar repair.

### 4. Compile and verify once

1. Wait for Overleaf to save, then run **Recompile** explicitly.
2. Wait for completion without repeatedly polling unchanged state.
3. Repair compile errors if present. Recompile again only after a repair or a
   visually consequential revision.
4. Inspect only affected PDF pages. For visual work, check clipping, overlap,
   legibility, whitespace, caption placement, alignment, and page budget.
5. Verify that the final source and PDF correspond to the intended batch.

### 5. Finalize review in one browser pass

- Resolve only comments whose requested changes were implemented and verified.
  Leave blocked or partially addressed comments unresolved; never delete them.
- Perform comment resolution as one browser-side loop: after each click,
  dynamically reacquire the remaining matching cards inside the same tool call.
  Do not return to the model between individual comments or reuse stale node IDs.
- Verify the intended in-scope tracked-change and unresolved-comment counts are
  zero, or explicitly report the items intentionally left pending.
- Create exactly one final label:

```text
Codex YYYY-MM-DD HH:MM TZ | process author review
```

- Verify both the before and final labels in **History > Labels**, return to the
  editor, restore **Reviewing** mode, and leave the affected PDF page visible.

## Large review batches and subagents

Use subagents only when the batch spans multiple independent files/sections or
contains enough substantive items that parallel analysis materially saves time.
Do not use them for an ordinary small review.

1. The coordinator performs the complete inventory and freezes one source
   snapshot.
2. Give each subagent a disjoint section and request proposed edits only.
3. Subagents do not access the live Overleaf tab.
4. The coordinator reconciles notation and semantic conflicts, then performs a
   single live edit, compile, resolution, and labeling sequence.

Parallelize analysis, never live-project mutation.

## Direct and visual edits

- Apply the smallest coherent batch and compile explicitly.
- For visual changes, inspect the right-hand PDF and iterate until acceptable.
- After successful verification, create one final label:

```text
Codex YYYY-MM-DD HH:MM TZ | concise change summary
```

- Use a pre-edit rollback label only for risky multi-file or destructive work.
- Do not label transient visual experiments.

## Efficiency and failure rules

- Do not remain silent for more than 60 seconds during browser work.
- Prefer a single browser script that performs a stable sequence over repeated
  model--browser round trips.
- After one failed UI strategy, inspect fresh state and change approach; do not
  repeat the same interaction without new evidence.
- Do not scan local repositories during a live Review unless a source-of-truth
  conflict must be resolved.
- If compilation cannot be repaired, restore the pre-edit state and do not label
  the failed version as complete.

## Handoff

Report the file or sections changed, accepted and unresolved item counts,
compile status, PDF pages inspected, and exact History label(s). Keep the live
project tab open for the user.
