# AI for Academic Writing

An author-first plugin for Codex and Claude Code. It packages four primary skills:

- `write-insightful-topconf-paper`: build and audit insight-driven ML papers;
- `github-paper-review-workflow`: revise Chinese semantic Markdown and formal English LaTeX through GitHub PR review;
- `manage-paper-experiments`: maintain the paper-wide experiment ledger and reproducible execution queues;
- `plot-paper-experiments`: produce traceable publication figures from experiment data.

## Optional integrations

The plugin does not bundle or auto-install external skills. It uses these capabilities when they are already available and degrades explicitly when they are absent:

| Integration | Used for |
|---|---|
| `citation-verifier` | DOI, arXiv, URL, and bibliography validation |
| `tavily-search`, `tavily-research`, `tavily-extract` | related-work discovery and primary-source extraction |
| `scientific-schematics` | method and pipeline diagrams |
| `scientific-visualization` | lower-level publication plotting support |
| `wandb-query`, `wandb-primary` | W&B run, metric, and artifact access |
| `apple-numbers-reader` | Apple Numbers experiment records |
| `pdf` | rendered-paper inspection |

Missing integrations must be reported as verification gaps; they must not be simulated.

## Install in Codex

```bash
codex plugin marketplace add vanzll/ai-for-academic-writing --ref main
codex plugin add ai-for-academic-writing@ai-for-academic-writing
```

## Install in Claude Code

```bash
claude plugin marketplace add vanzll/ai-for-academic-writing
claude plugin install ai-for-academic-writing@ai-for-academic-writing
```

For local development:

```bash
claude --plugin-dir ./plugins/ai-for-academic-writing
```

The repository is private by default, so GitHub authentication must grant access.

## Review identity contract

The paper-review workflow supports a human author and an AI agent using the same GitHub account. Every AI-authored PR body or comment contains a reserved `<!-- academic-writing-ai:... -->` marker. Unmarked comments from authorized author accounts retain highest priority. The agent never merges or resolves human review threads without explicit approval.
