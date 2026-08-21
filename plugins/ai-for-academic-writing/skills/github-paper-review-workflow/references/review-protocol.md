# Author-first review protocol

## Identity model

The human author and the agent may authenticate through the same GitHub login. Login identity alone therefore cannot distinguish authorship.

Reserved prefix:

```html
<!-- academic-writing-ai:
```

Every agent-authored PR body or comment must contain this prefix. Any unmarked message from an authorized author login is a human instruction. Never add the marker to human-authored content or rewrite existing comments.

Recommended markers:

```html
<!-- academic-writing-ai:pr-body -->
<!-- academic-writing-ai:response source_id=PRRC_xxx commit=abc1234 -->
<!-- academic-writing-ai:status source_id=IC_xxx commit=abc1234 -->
```

`source_id` is the GraphQL node ID or REST database ID of the human comment being addressed. One response may cite multiple source IDs only when the implementation is genuinely shared.

## Instruction precedence

Use this order:

1. Newest unresolved human review comment.
2. Newest unmarked human top-level PR comment.
3. Chinese semantic Markdown.
4. English LaTeX.
5. Agent judgment.

An explicit later correction supersedes an earlier instruction. A thread becoming outdated does not erase the instruction. Resolution indicates author acceptance; an AI reply does not.

## Review surfaces

Collect all three surfaces:

1. Issue comments on the pull request.
2. Pull-request review summaries.
3. Inline review-thread comments, including `isResolved` and `isOutdated`.

`gh pr view --comments` alone is incomplete because it does not provide reliable review-thread resolution state.

## Scope and synchronization

- Prefer one draft PR per coherent section or revision objective.
- Maintain stable claim/paragraph IDs if the Chinese and English structures differ.
- Update semantic content in Chinese before polishing English.
- Do not translate literally when a shorter formal English statement preserves the intended claim.
- A requested English wording change may be applied directly, but mirror any semantic change into Chinese.

## Merge policy

The agent may prepare a PR but must not merge or resolve human threads without explicit authorization. Required merge conditions:

- no unaddressed human instructions;
- no unresolved human threads;
- successful required checks;
- successful LaTeX compile and visual inspection;
- synchronized Chinese/English semantics;
- explicit author approval.

If repository visibility is public, stop unless public operation was explicitly authorized. Academic drafts, anonymous submissions, review responses, and unpublished results are sensitive by default.
