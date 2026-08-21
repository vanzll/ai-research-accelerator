# GitHub command reference

## Repository and pull request

```bash
gh repo view --json nameWithOwner,visibility,isPrivate,url
gh pr view <pr> --json number,url,title,state,isDraft,headRefName,baseRefName,reviewDecision,statusCheckRollup
```

## Inline review reply

Reply to an existing inline comment by numeric REST ID:

```bash
gh api --method POST \
  repos/OWNER/REPO/pulls/PR/comments/COMMENT_ID/replies \
  -f body='<!-- academic-writing-ai:response source_id=NODE_ID commit=SHA -->
Implemented in SHA: concise summary.'
```

Do not call a resolve-thread mutation unless the author explicitly asks.

## Top-level response

```bash
gh pr comment <pr> --body '<!-- academic-writing-ai:response source_id=NODE_ID commit=SHA -->
Implemented in SHA: concise summary.'
```

## Draft PR body

```markdown
<!-- academic-writing-ai:pr-body -->
## Scope
...

## Validation
- [ ] LaTeX compiles
- [ ] Changed pages visually inspected
- [ ] Chinese and English sources synchronized
```

## Safety checks

Before any write:

```bash
git status --short
git fetch --prune origin
gh repo view --json visibility,isPrivate
```

Never use `git reset --hard`, overwrite an author's branch, or silently discard local edits.
