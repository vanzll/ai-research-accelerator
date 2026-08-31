---
name: edit-overleaf-with-edge
description: Edit an open Overleaf paper through the user's Edge browser extension, compile and inspect the rendered PDF, iterate on visual changes, and preserve every completed edit batch with a timestamped Overleaf History label. Use when the user asks Codex to modify, compile, review, or visually refine an Overleaf project in Edge.
---

# Edit Overleaf With Edge

Use the live, signed-in Overleaf tab in Microsoft Edge as the editing surface.
Read and follow `browser:control-in-app-browser` before browser interaction, and
select Edge explicitly. Do not substitute another browser.

## Establish the editing contract

- Claim the already-open Overleaf tab by its fresh title and URL. Do not guess a
  tab ID or open a duplicate project when the intended tab is available.
- Confirm the project, target file, requested scope, and visible current state
  before editing.
- If an active GitHub paper PR or another synchronized source is currently
  authoritative, do not create concurrent Overleaf edits unless the author has
  explicitly chosen Overleaf as the active editing surface. Surface the conflict
  instead of silently forking the paper state.
- Keep changes within the requested logical batch. Preserve unrelated author or
  collaborator edits.

## Edit, compile, and verify

1. Inspect the current source and, when layout matters, the relevant rendered
   page before editing. For a risky multi-file change, create a labeled rollback
   checkpoint first.
2. Apply the smallest coherent source change in Overleaf and wait until its
   save state has settled.
3. Explicitly run **Recompile** after every logical edit batch. Do not treat
   autosave or an old PDF preview as successful verification.
4. Wait for compilation to finish. Inspect compile errors and the resulting PDF
   before continuing. Repair failures rather than leaving a broken current
   state.
5. For figures, tables, equations, page budgets, or other visual changes,
   inspect the right-hand PDF preview at the affected page. Check clipping,
   overlap, legibility, whitespace, caption placement, panel alignment, and
   consistency with nearby content. Iterate source edit, recompile, and visual
   inspection until the result is acceptable.
6. Recheck that the final source contains the intended change and that the PDF
   preview corresponds to the latest successful compile.

## Label every completed modification

After successful compilation and any required visual inspection, label the
exact final project version in Overleaf History. One label covers one completed
logical edit batch; do not label transient visual experiments.

Use this format with the user's local timezone:

```text
Codex YYYY-MM-DD HH:MM TZ | concise change summary
```

For example:

```text
Codex 2026-08-31 14:32 SGT | refine Figure 3 gradient comparison
```

The label is mandatory. Verify that it appears in **History > Labels** and
points to the final compiled state, then return to the editor. If the final
state cannot compile and cannot be repaired, restore the pre-edit state; do not
mislabel a failed edit as completed.

## Handoff

- Leave the project open in Edge with the latest compiled PDF visible on the
  right, preferably at the changed page.
- Keep the live project tab available to the user.
- Report the files or sections changed, compile status, visual checks performed,
  and the exact History label created.
