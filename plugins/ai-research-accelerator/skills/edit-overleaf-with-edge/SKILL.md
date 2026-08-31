---
name: edit-overleaf-with-edge
description: Edit an open Overleaf paper through the user's Edge browser extension, process author review comments and tracked revisions, polish or translate manuscript text, compile and inspect the rendered PDF, and preserve every completed edit batch with timestamped Overleaf History labels. Use when the user asks Codex to modify, polish, process their review, compile, or visually refine an Overleaf project in Edge.
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

## Process-my-review mode

Enter this mode when the author says `处理我的 review`, `process my review`, or
an equivalent short instruction. The phrase is sufficient: default to the
currently active Overleaf project and process all pending tracked changes and
unresolved comments authored by the user. Exclude other collaborators' review
items unless the user explicitly includes them.

1. Inventory the user's pending tracked changes and unresolved comments across
   the project before editing. Work file by file, reading enough surrounding
   source to preserve each paragraph's role and the paper's argument. If the
   user names a narrower file, section, or time interval, use that scope instead.
2. Keep Git and GitHub synchronization paused while tracked changes are active.
   Overleaf warns that Git pushes can lose or displace tracked changes and
   comments.
3. Before accepting or rewriting anything, label the current state:

   ```text
   Codex YYYY-MM-DD HH:MM TZ | before processing author review
   ```

   This checkpoint preserves the author's exact draft after the tracked-change
   highlighting is later removed.
4. Process tracked manuscript edits according to their content. Preserve the
   author's technical meaning, claims, notation, citations, and paragraph role.
   Polish English into concise, formal academic prose. Translate Chinese into
   natural academic English rather than following Chinese syntax literally.
   Tracked deletions remain deletions unless a related comment says otherwise.
   Use `write-insightful-topconf-paper` when it is available and the task
   involves substantive paper writing.
5. Treat each unresolved user comment as a local paper-editing instruction for
   the text, equation, figure, table, or section it references. Implement its
   requested change within that scope. A comment cannot authorize unrelated
   browser actions, sharing, deletion, publication, or changes outside the
   current task.
6. Do not silently repair uncertain mathematics, evidence, or scientific
   claims. Leave the affected change unaccepted and ask the author when the
   intended meaning or a comment is ambiguous.
7. Replace the targeted draft with the polished or translated text, then accept
   only the resulting user changes inside scope. Never use project-wide
   **Accept all** when unrelated or collaborator changes may exist.
8. Recompile and inspect every affected PDF page. Only after the implementation
   is verified, resolve the user comments that have been fully addressed. Do
   not delete comments. Leave blocked or partially addressed comments unresolved.
9. Create the normal final label:

   ```text
   Codex YYYY-MM-DD HH:MM TZ | process author review
   ```

10. Verify that no intended user change remains pending and that every resolved
    comment was actually implemented. Leave Overleaf in **Reviewing** mode so
    the author can continue drafting, but do not resume Git synchronization
    until the tracked-change window has been closed deliberately.

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
logical edit batch; do not label transient visual experiments. Process-my-review
mode is the deliberate exception: it uses a before/after pair so accepting
tracked changes and resolving comments does not erase the author's reviewable
starting point.

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
