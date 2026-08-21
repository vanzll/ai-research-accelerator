---
name: plot-paper-experiments
description: Create publication-ready machine-learning experiment figures from W&B or local tabular data, especially RL training/evaluation curves, ablations, scaling plots, and benchmark bars. Use when Codex must retrieve run histories, compare methods, establish paper-facing plot semantics, render conference-quality figures, or preserve reproducible figure data and metadata.
---

# Plot Paper Experiments

Create honest, compact figures whose visual language is close to strong diffusion-RL papers. When installed, use `wandb-query` for W&B retrieval and `scientific-visualization` for rendering details; otherwise use exported local tables and the project's plotting stack, and disclose the missing integration. Read [references/visual-contract.md](references/visual-contract.md) before proposing or producing a figure.

## Workflow

### 0. Treat user review as template training data

This skill is expected to improve through repeated author review. After every user critique or approval:

1. Separate figure-specific preference from a reusable plotting rule.
2. Apply the requested change to the current figure only after updating and reconfirming the plot contract when names or colors change.
3. When the feedback expresses a reusable preference, update this skill or its visual reference in the same turn.
4. Preserve prior approved rules unless the latest feedback explicitly supersedes them.
5. Validate the skill after every edit and state which reusable rule changed.

Do not overfit one data-specific request into a universal rule. For example, a particular y-limit belongs in figure metadata; the rule that no traversed interval may be omitted belongs in this skill.

### 1. Establish the evidence

1. Identify the scientific claim, target venue, final column width, benchmark, methods, seeds, x-axis budget, and train-versus-eval semantics.
2. Read each W&B run's config, state, summary, and targeted history. Fetch sparse metrics such as train and eval in separate history requests.
3. Verify that compared x values have the same meaning. Do not silently equate optimizer updates, rollout epochs, samples, wall time, or GPU hours.
4. Preserve stopped or collapsed runs at their actual endpoint. Never forward-fill them.

### 2. Pass the mandatory plot-contract gate

Before rendering, provide a concise recommendation table and wait for user confirmation. Do not infer that an earlier figure's labels or colors are approved for a new semantic comparison.

Include exactly:

| Item | Recommended value | Reason or mapping |
|---|---|---|
| Figure purpose | claim the panel supports | paper role |
| X-axis label | exact display text | exact W&B field and conversion |
| Y-axis label | exact display text | exact metric and transformation |
| In-plot title | exact text or `None` | default to `None`; use caption/subfigure label |
| Legend labels | ordered paper-facing names | run IDs mapped to each name |
| Colors | name and hex per method | also state line style and marker |
| Y-axis | limits and break treatment | include omitted range and why |
| Curve treatment | raw, smoothed, mean/band | smoothing and uncertainty semantics |

The user must explicitly confirm each of these fields: x-axis name, y-axis name, every legend display name, title text or absence of a title, and every method-color assignment. Confirmation is revision-specific: if feedback causes any field to change, present the changed contract and obtain confirmation again before rendering. A request such as `draw it`, `revise it`, or `try again` approves execution only; it does not approve newly invented names or colors. If the user explicitly delegates naming/color decisions or approves a persistent house style, record the scope of that delegation and proceed.

For a single-curve figure, still confirm whether to show a legend and, if so, its exact display name. Do not silently add suffixes such as `(Ours)`, `EMA`, `Train`, model names, or benchmark names.

Never expose raw W&B display names in a paper figure. Recommend concise canonical method names such as `StableCov (ours)`, `DiffusionNFT`, and `Flow-GRPO`.

### 3. Build a reproducible data artifact

1. Save tidy CSV or Parquet with run ID, source URL, series, metric, x, value, seed, and any aggregation fields.
2. Save metadata containing the approved plot contract, exact history keys, smoothing, uncertainty definition, data exclusions, generated time, and code version.
3. Keep data retrieval separate from styling so the plot can be regenerated without querying W&B.

### 4. Render the approved figure

- Default to no in-plot title. Put benchmark/model context in the caption or subfigure label unless the user approves a title.
- Use benchmark-specific y labels such as `GenEval Score`, `OCR Accuracy`, or `PickScore`, not generic `Reward`, when the metric is known.
- Prefer one clean curve per method. Do not default to a pale raw line plus a same-color EMA line.
- Show markers at meaningful logged/eval points. Use line style and marker differences in addition to color.
- Prefer dense small markers joined by thin straight segments so the reader sees
  the sampled trajectory rather than a thick ribbon. Keep a regular marker rhythm
  in x-axis units; avoid both noisy raw spaghetti and sparse chunky markers. Use
  no grid or a very subtle grid according to the approved reference style.
- When straight connectors between visible markers are requested, plot only those
  selected marker vertices. Do not use `markevery` on a full-resolution polyline,
  because hidden intermediate vertices make the apparent connector curved. Save
  the full series separately and record the display-subsampling rule.
- Evaluate marker density and size at the intended publication dimensions. A
  numerically small step interval is not enough when markers render too small or
  too far apart to establish the reference figure's visual rhythm.
- Match an approved reference using the axes aspect ratio, not just the outer
  image dimensions. Account explicitly for external legends and reserve their
  space without flattening the data panel.
- When smoothing is needed for presentation, keep it causal, identical in x-axis
  units across methods, disclosed in metadata/caption, and weak enough to retain
  collapse, recovery, and stopping behavior.
- Use a colorblind-safe palette, but confirm exact method-color assignments before rendering.
- For multiple seeds, show the declared aggregate and band. For one seed, do not fabricate uncertainty.
- Keep train and held-out eval in separate panels or separate figures by default. A training-curve figure must not mix dense train reward with sparse held-out evaluation merely because both are available. Combine them only when the scientific claim explicitly requires it and the user approves.
- Place the legend centered below the axes by default, outside the data region. Use an in-axis legend only when the user approves it for a specific layout.

### 5. Handle nonzero y ranges honestly

Do not waste most of a panel on an empty `0`-to-data region.

- If the curve starts at a nonzero value `y_start`, use one continuous axis from approximately `y_start` through the full observed range. Add a visible diagonal or zigzag break mark at the bottom of the y spine to disclose that only `0` to `y_start` is omitted. Do not omit any interval traversed by the curve.
- If an isolated low baseline must be shown together with upper curves, use a true two-part broken y-axis with shared x, diagonal break marks on both panes, and no continuous vertical spine through the omitted interval.
- Never draw a low baseline inside a large empty panel merely to force zero onto the axis.
- State the omitted interval in the plot contract and metadata.

### 6. Verify at final size

1. Export vector PDF plus 600-DPI PNG.
2. Inspect the raster at intended print size, not only zoomed in.
3. Verify embedded fonts, non-overlapping labels, line visibility, legend ordering, break marks, and grayscale distinguishability.
4. Check that every plotted point can be traced to the saved data artifact.

### 7. Require independent layout review

Before delivering a figure, launch an independent subagent to review the final PNG/PDF at intended print size. Give it the artifact, intended dimensions, and approved plot contract, but do not provide your own diagnosis or desired verdict.

Require the reviewer to inspect:

- clipping, overlap, alignment, whitespace, and panel balance;
- axis-label, tick, legend, and annotation readability at final size;
- legend placement and ordering;
- line/marker distinguishability in color and grayscale;
- whether truncation or break marks communicate the omitted range honestly;
- whether any visual choice exaggerates, hides, or ambiguously represents the data;
- consistency with the approved contract and surrounding paper figures.

Resolve concrete layout failures and repeat the independent review after material changes. If subagent capability is unavailable, explicitly report that independent review was not performed; never imply that self-inspection was independent review.

## Deliverables

Return links to the PDF, PNG, plotting script, tidy data, and metadata. State the W&B run IDs and any caveat that changes interpretation.
