# Visual Contract

## Learning From Author Feedback

Treat author feedback as one of three scopes:

- **Figure-only:** exact limits, selected runs, caption wording, or one-off annotation. Store it in that figure's metadata.
- **Paper house style:** stable method colors, naming conventions, panel widths, legend placement, or typography. Record it here after explicit approval.
- **General integrity rule:** truthful axes, uncertainty semantics, provenance, and no forward filling. Record it in `SKILL.md` and apply it universally.

When scope is ambiguous, keep the change figure-specific and ask before promoting it into the template. Record rejected prototypes so they are not silently reused.

## Reference Language

The preferred visual language is informed by the official papers:

- DiffusionNFT: https://arxiv.org/pdf/2509.16117
- Flow-GRPO: https://arxiv.org/pdf/2505.05470

Observed conventions worth retaining:

- No large in-plot title; scientific context lives in axis labels, panel labels, and captions.
- Benchmark-specific axes such as `OCR Score`, `PickScore`, `GenEval Score`, `Training Iterations`, `Training Steps`, and `Training Time (GPU Hours)`.
- Compact legends centered below the plotting axes by default. Use unused in-axis
  space only when the author explicitly approves it for a particular figure.
- Continuous colored trajectories built from dense, small data markers joined by
  thin straight segments on a white background. Avoid both visibly jagged raw
  spaghetti and thick ribbon-like curves that hide the sampled trajectory.
- Truncated y ranges around the informative interval. DiffusionNFT Figure 1 uses a broken y-axis when a low pretrained baseline must coexist with high-performing curves.
- The emphasized method is warm orange/vermillion and the main baseline is blue in DiffusionNFT head-to-head figures. Flow-GRPO uses additional muted green/teal/orange series plus marker and dash differences.

Do not reproduce these figures literally. Use their information density and hierarchy as the reference.

## Default Recommendation Palette

Treat this only as the first proposal. Confirm assignments for every figure.

| Role | Color | Hex | Default style |
|---|---|---|---|
| Ours / emphasized | Vermillion | `#D55E00` | solid, circle |
| Primary baseline | Blue | `#0072B2` | solid, square |
| Secondary baseline | Bluish green | `#009E73` | dashed, triangle |
| Additional method | Reddish purple | `#CC79A7` | dash-dot, diamond |
| Reference/pretrained | Gray | `#7A7A7A` | dotted |

Never rely on hue alone. Assign stable line styles and markers, and test grayscale output.

## Recommended RL-Curve Contract

- `x`: use the budget named by the claim. Prefer `Training Steps` for an equal-step comparison and `Training Time (GPU Hours)` for an efficiency claim. Never label `_step` without verifying its semantics.
- `y`: use the benchmark's public name. Add `Train` or `Eval` only when needed to prevent ambiguity.
- `title`: default `None`. Use `(a) OCR`, `(b) GenEval`, or caption text outside the plotting area for multi-panel figures.
- `legend`: method names only. Put protocol details such as model, CFG, and seed in the caption unless they distinguish curves.
- `line`: one publication curve per method. Use raw curves only for a dynamics/instability figure whose claim requires raw variation.
- `smoothing`: if used, use a causal method and disclose its window in metadata/caption. Apply identical smoothing in x-axis units to all methods.
- `trajectory aesthetics`: when dense logging makes a curve visually fragmented,
  first recommend a disclosed causal smoother, dense small markers at a regular
  x-axis rhythm, thin straight connectors, and reduced grid prominence. Never
  smooth away a collapse, recovery, stopping point, or other event central to the
  claim.
- `straight marker connectors`: if the author requests straight segments between
  visible markers, subsample the plotted polyline to those marker vertices before
  calling the renderer. `markevery` alone is insufficient because hidden
  intermediate vertices still bend the line. Preserve the full-resolution series
  separately and disclose display subsampling.
- Judge marker density at the final rendered physical size, not only by the
  numerical step interval. Reference-style dense markers must remain individually
  visible and form the dominant trajectory rhythm rather than disappearing into
  the connector.
- When matching a reference figure, compare the plotting-area aspect ratio rather
  than only the full raster canvas. External legends and captions can change the
  canvas ratio substantially; record both figure dimensions and axes geometry.
- `eval`: keep sparse evaluation points out of the dense training-curve panel by default. Use a separate evaluation panel/figure; if explicitly combined, use unconnected markers unless connecting them is approved.
- `legend`: center it below the plotting axes by default so it cannot cover dynamics or collapse regions.

## Y-Axis Breaks

Use one of two forms:

1. **Truncated continuous pane:** plot `[y_start, y_max]` continuously and draw a small double diagonal/zigzag symbol at the bottom of the y spine. This marks omission of `[0, y_start)` only. Never remove a middle interval that the curve actually traverses.
2. **Two-pane break:** retain a short lower pane for a low baseline and a tall upper pane for training curves. Share x, remove touching spines, and draw matched diagonal break marks. Do not interpolate across the gap.

Choose limits from the scientific comparison, not from a rule that maximizes visual separation. Keep enough margin that noise and collapse remain visible.

## Confirmation Template

Before rendering, present:

```text
Purpose: compare optimization speed and stability on OCR.
X-axis: Training Steps <- W&B _step (1:1).
Y-axis: OCR Accuracy <- eval/reward/avg.
Title: None; panel/caption carries OCR and model.
Legend: StableCov (ours), DiffusionNFT, Flow-GRPO.
Colors: ours #D55E00; NFT #0072B2; Flow-GRPO #009E73.
Styles: circle/solid; square/solid; triangle/dashed.
Y-axis: 0.55-1.00 with a break marking omitted 0-0.55.
Curve: sparse eval markers and approved connecting lines; no raw+EMA overlay.
```

Wait for confirmation before rendering.

## Confirmation Discipline

- Treat names and colors as scientific content, not cosmetic defaults.
- Confirm the literal x-axis string, literal y-axis string, title or `None`, ordered literal legend strings, and method-to-color mapping.
- When user feedback changes plot structure, issue a short delta contract listing every changed field. Do not carry over approval to a renamed field.
- `Make the legend lower`, `remove eval`, or other layout feedback does not authorize inventing a new method name.
- Store the approved literal strings and color hex values in metadata so later regeneration cannot silently drift.

## Independent Review Prompt

Use a fresh subagent with a neutral prompt similar to:

```text
Review this publication figure at its stated final dimensions. Check typography,
clipping, whitespace, alignment, legend placement, axis-break honesty, grayscale
distinguishability, and compliance with the attached plot contract. Report only
specific issues, ordered by severity; say clearly if no blocking issue exists.
```

Do not tell the reviewer which issue you expect it to find.
