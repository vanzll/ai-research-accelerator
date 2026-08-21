# Paper Reporting Protocol

## Training-Curve Evidence

Use the horizontal axis declared by the paper. If W&B step is the chosen axis, verify that its meaning is comparable across methods. Also retain rollout count, optimizer updates, reward calls, wall time, and GPU-hours for auditability.

Recommended curve summary:

| Field | Purpose |
|---|---|
| Initial / final step | Defines the observed horizon |
| Step to reward thresholds | Direct speed comparison |
| AUC on shared horizon | Overall sample efficiency |
| Peak / final / tail mean | Separates best case from sustained performance |
| Maximum drawdown | Stability |
| Collapse or active-stop step | Makes instability visible |
| Reward calls / GPU-hours | Compute and feedback efficiency |

Do not smooth away collapse. State smoothing parameters in the figure caption.

## Held-Out Evaluation

Report at least:

- best evaluation value and selected step;
- final evaluation value and final step;
- evaluator, version, and prompt split;
- checkpoint identity;
- termination status.

Best selection must use a pre-registered grid shared by compared methods. If one method has denser evaluation, restrict selection to the common grid or rerun missing points. A final-only baseline should not be compared against another method's unconstrained best without a visible qualifier.

When an evaluation at the exact terminal step exists only for the new method, keep it as final and exclude it from shared-grid best selection if the baseline lacks that point.

## Baselines and Failed Runs

- A deliberately stopped on-policy baseline after collapse is valid stability evidence.
- Its last evaluation is not equivalent to a stable completed final evaluation; report the stop reason.
- A baseline with known invalid hyperparameters is excluded from headline comparison and retained in the ledger as invalid.
- Historical runs may support motivation but should not silently replace formal protocol runs.
- Smoke tests validate infrastructure, not model quality.

## Multi-Reward

Record:

- aggregate train/eval score;
- every optimized reward component;
- every held-out metric;
- component weighting and normalization;
- checkpoint-selection metric.

Avoid choosing a checkpoint independently for each component unless the paper explicitly defines that protocol.

## Pairwise Training

Keep binary/tie labels separate from evaluation reward. Training may use 0/1 pairwise labels while W&B train/eval reporting uses the underlying real reward; record both namespaces clearly. Report tie fraction and effective non-tie sample fraction.

## Table Hygiene

- Include the method budget in the row or caption.
- Use consistent decimal precision.
- Mark missing, stopped, invalid, and not-applicable values differently.
- Link each result row back to a paper experiment ID and W&B run.
- Preserve the raw extraction used to generate tables.
- Never select the best result after looking across undeclared seeds, horizons, or evaluator variants.

## Paper Evidence Coverage

Before declaring the experiment program complete:

- diff the paper plan against the ledger;
- verify that every planned main-table row, curve, ablation, scaling result, and mechanism claim has a source row;
- separate required missing runs from optional extensions and protocol conflicts;
- verify historical evidence has direct links and key numbers, even when it is excluded from headline tables;
- ensure a future writer can reconstruct every paper-facing number from the ledger without relying on chat history.

## W&B-Grounded Ledger Updates

Before every user-requested ledger update, query W&B for each affected run and record its exact display name, run ID/URL, state, resolved config, summary, and the history rows supporting the compact result synopsis. If a planned run has no W&B identity yet, keep it `not-started`, `reserved`, or `queued`; do not infer `running` from tmux, logs, GPU use, or a remote agent's launch claim.

After delegating a launch, update the ledger only when the remote agent reports a verified W&B startup handshake. Record both the expected and observed display name when naming differs. Preserve every failed attempt and link retries explicitly.
