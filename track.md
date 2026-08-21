# Development Track

## 2026-08-21: Initial dual-agent plugin

- Initial repository/plugin name: `ai-for-academic-writing`; renamed to `ai-research-accelerator` before wider use.
- Display name: **AI Research Accelerator**. Tagline: **AI for Accelerating Research**.
- Distribution layout: one marketplace repository containing `plugins/ai-research-accelerator`, with both Codex and Claude Code manifests and shared Agent Skills.
- Main skills:
  - `write-insightful-topconf-paper`
  - `github-paper-review-workflow`
  - `manage-paper-experiments`
  - `plot-paper-experiments`
- Optional, unbundled integrations are documented in `README.md`: citation verification, Tavily research, scientific schematics/visualization, W&B, Apple Numbers, and PDF inspection.
- GitHub paper review uses Chinese semantic Markdown plus formal English LaTeX. Newest human review feedback has highest priority.
- Human and AI may use the same GitHub login. Every AI-authored GitHub message must contain `<!-- academic-writing-ai:... -->`; an unmarked message from an authorized login is treated as human instruction.
- The agent must not merge or resolve human review threads without explicit author approval.
- `collect_review_state.py` is read-only, defaults to private repositories, gathers all review surfaces, and fails closed when thread state is unavailable.
- Local validation passed:
  - `python scripts/validate_repo.py`
  - `python -m unittest discover -s tests -v`
  - Codex `quick_validate.py` for all four skills
  - Codex `validate_plugin.py`
  - `claude plugin validate .`
- Private GitHub repository after rename: `https://github.com/vanzll/ai-research-accelerator`.
- Initial published implementation commit: `94878f8ee42f618c7bbb24784d4a98bb46fad3ca`.
- GitHub Actions `Validate plugin` passed for the initial commit.
- A clean, isolated `CODEX_HOME` successfully installed the original package before rename; the renamed package is revalidated separately.
