---
name: github-paper-review-workflow
description: Run author-first academic paper revisions through GitHub pull requests. Use when creating section-specific paper PRs, maintaining a Chinese semantic Markdown source alongside formal English LaTeX, collecting GitHub review comments and unresolved threads, distinguishing human author instructions from AI replies made by the same account, revising a paper from review feedback, or auditing whether a paper PR is ready to merge.
---

# GitHub Paper Review Workflow

Use GitHub as the source of truth for paper revisions. Maintain two authoring surfaces:

- a Chinese semantic Markdown file for claims, logic, and author instructions;
- a formal English LaTeX file for the submission text.

Keep both synchronized, but treat the Chinese file as semantic authority unless a newer human review comment overrides it.

## Non-negotiable rules

1. Apply this priority order: newest unresolved human review instruction, Chinese semantic source, English LaTeX, agent judgment.
2. Never merge, resolve a human thread, or force-push without explicit author approval.
3. Never edit the Overleaf copy concurrently with an active GitHub PR. GitHub is authoritative until the PR closes.
4. Never silently weaken a mathematical claim or ignore contradictory evidence. Explain the conflict and block when needed.
5. Mark every AI-created PR body, issue comment, review reply, and status message with the reserved marker `<!-- academic-writing-ai:`. Never post an unmarked AI comment.
6. Treat an unmarked comment from an authorized author login as human instruction, even when `gh` uses the same login.
7. Default to private repositories. Fail closed on a public repository unless the author explicitly permits it.

Read [references/review-protocol.md](references/review-protocol.md) before creating or processing a PR. Read [references/github-commands.md](references/github-commands.md) when issuing GitHub API commands.

## Workflow

### 1. Establish scope

- Identify the exact paper section and the Chinese/English source paths.
- Inspect repository instructions, current branch, dirty files, remote state, and open PRs.
- Create a section-specific branch. Preserve unrelated user changes.
- Assign stable paragraph or claim IDs in both sources when review mapping would otherwise be ambiguous.

### 2. Open a draft PR

- Update the Chinese semantic source first, then produce the concise English LaTeX.
- Compile the paper and inspect the rendered PDF before pushing.
- Open a draft PR with scope, claims changed, evidence dependencies, compile status, and open questions.
- Put `<!-- academic-writing-ai:pr-body -->` in the PR body.

### 3. Collect author feedback

Run the bundled read-only audit:

```bash
python scripts/collect_review_state.py --pr <number-or-url> --format markdown
```

Pass `--author-login <login>` for every authorized human reviewer. Without it, the authenticated `gh` login is the sole authorized author.

The audit must include:

- top-level PR comments;
- review summaries;
- inline comments and complete review-thread resolution state;
- CI checks and PR metadata;
- AI responses linked to source comment IDs.

Do not revise from a partial `gh pr view` snapshot when inline review threads may exist.

### 4. Build an author-lock checklist

Before editing, convert every active human instruction into a checklist with source URL, target text, requested action, and conflicts. Newer human comments override older conflicting comments. Do not infer that an AI reply resolves a human instruction.

### 5. Revise and validate

- Apply semantic changes to the Chinese Markdown and corresponding prose/math to the English TeX.
- Preserve exact author wording where a review suggestion explicitly locks wording.
- Keep Observation/Insight callouts concise and claim-like; move evidence and derivations to surrounding prose or appendices.
- Compile LaTeX, inspect changed pages, run repository checks, and review the staged diff.
- Commit only intended source files and required bibliography/figure changes. Follow repository policy for generated PDFs.

### 6. Respond without impersonating the author

Reply to each addressed instruction with the implementing commit and a short summary. Start every AI response with:

```html
<!-- academic-writing-ai:response source_id=<github-id> commit=<sha> -->
```

Leave inline threads unresolved for the author. For a rejected or blocked request, state the evidence or mathematical conflict rather than pretending it was implemented.

### 7. Enforce the merge gate

Report ready only when:

- all human instructions are addressed or explicitly superseded;
- all human review threads are resolved by the author;
- required CI checks pass;
- LaTeX compiles and changed pages pass visual inspection;
- Chinese and English sources agree semantically;
- the author explicitly approves merging.

The audit script is advisory and fail-closed. It never edits GitHub state.

## Improve this skill from feedback

When author feedback exposes a reusable workflow failure, update this skill after finishing the immediate paper revision. Generalize the rule, keep it concise, add or update deterministic tests when behavior changes, validate the skill, and avoid encoding one paper's terminology as a universal rule.
