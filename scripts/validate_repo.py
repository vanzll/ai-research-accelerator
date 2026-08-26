#!/usr/bin/env python3
"""Dependency-free validation for the dual Codex/Claude plugin repository."""

from __future__ import annotations

import json
import py_compile
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "ai-research-accelerator"
REQUIRED_SKILLS = {
    "github-paper-review-workflow",
    "long-task-relay",
    "manage-paper-experiments",
    "multinode-training",
    "plot-paper-experiments",
    "shared-filesystem-agent-coordination",
    "write-insightful-topconf-paper",
}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return value


def validate_skill(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "[" + "TODO" in text or "TODO" + ":" in text:
        raise AssertionError(f"placeholder remains in {path}")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise AssertionError(f"missing YAML frontmatter in {path}")
    frontmatter = match.group(1)
    expected_name = path.parent.name
    if not re.search(rf"^name:\s*{re.escape(expected_name)}\s*$", frontmatter, re.MULTILINE):
        raise AssertionError(f"frontmatter name does not match {expected_name}")
    description = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    if not description or len(description.group(1).strip()) < 40:
        raise AssertionError(f"description is missing or too short in {path}")


def main() -> int:
    codex = load_json(PLUGIN / ".codex-plugin" / "plugin.json")
    claude = load_json(PLUGIN / ".claude-plugin" / "plugin.json")
    codex_market = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    claude_market = load_json(ROOT / ".claude-plugin" / "marketplace.json")

    for manifest in (codex, claude):
        assert manifest["name"] == "ai-research-accelerator"
        assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
    assert codex["version"] == claude["version"] == claude_market["version"]
    assert codex_market["plugins"][0]["source"]["path"] == "./plugins/ai-research-accelerator"
    assert claude_market["plugins"][0]["source"] == "./plugins/ai-research-accelerator"

    skill_names = {path.name for path in (PLUGIN / "skills").iterdir() if path.is_dir()}
    assert REQUIRED_SKILLS <= skill_names, f"missing skills: {sorted(REQUIRED_SKILLS - skill_names)}"
    for skill in REQUIRED_SKILLS:
        validate_skill(PLUGIN / "skills" / skill / "SKILL.md")

    for script in PLUGIN.rglob("*.py"):
        py_compile.compile(str(script), doraise=True)
    print(f"validated plugin {codex['name']} {codex['version']} with {len(REQUIRED_SKILLS)} main skills")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, json.JSONDecodeError, py_compile.PyCompileError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
