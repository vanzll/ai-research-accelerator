#!/usr/bin/env python3
"""Run lightweight, deterministic checks on a LaTeX paper source tree."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


UNRESOLVED_PATTERNS = {
    "TODO marker": re.compile(r"\bTODO\b", re.IGNORECASE),
    "FIXME marker": re.compile(r"\bFIXME\b", re.IGNORECASE),
    "citation placeholder": re.compile(r"\[(?:CITATION|REF(?:ERENCE)?)\s+NEEDED\]", re.IGNORECASE),
    "undefined reference warning in source": re.compile(r"\?\?"),
}

STYLE_PATTERNS = {
    "throat-clearing phrase": re.compile(
        r"\b(?:it is (?:important|worthwhile) to note|in this section,? we (?:will )?(?:discuss|describe|present))\b",
        re.IGNORECASE,
    ),
    "inflated stock phrase": re.compile(
        r"\b(?:delve into|plays? a (?:crucial|pivotal) role|paradigm shift|seamlessly integrates?)\b",
        re.IGNORECASE,
    ),
    "informal mechanism term": re.compile(
        r"\b(?:push[-–—]+pull|push and pull|pushing away|sideways movement|"
        r"signal (?:is |gets )?swallowed)\b",
        re.IGNORECASE,
    ),
}

CALLOUTS = ("observation", "insight", "keyequation")
FORMAL_RESULTS = ("lemma", "proposition", "theorem", "corollary")
COUNTED_ENVIRONMENTS = CALLOUTS + FORMAL_RESULTS + ("proof",)
MAX_CALLOUT_WORDS = 45
MAX_CALLOUT_TITLE_WORDS = 10
INSIGHT_IMPERATIVE_START = re.compile(
    r"^(?:add|aggregate|apply|build|choose|compute|construct|define|design|"
    r"estimate|optimize|remove|replace|restore|set|train|use)\b",
    re.IGNORECASE,
)


def tex_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*.tex") if ".git" not in p.parts)


def strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        match = re.search(r"(?<!\\)%", line)
        lines.append(line[: match.start()] if match else line)
    return "\n".join(lines)


def line_number(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def prose_text(text: str) -> str:
    text = re.sub(r"\\label\{[^}]*\}", " ", text)
    text = re.sub(r"\\(?:cite\w*|ref|eqref|Cref|cref)\{[^}]*\}", " ", text)
    text = re.sub(r"\$[^$]*\$", " MATH ", text)
    text = re.sub(r"\\[a-zA-Z@]+\*?(?:\[[^\]]*\])?", " ", text)
    text = re.sub(r"[{}\\]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", prose_text(text)))


def findings_for_file(
    path: Path, check_formal_explanation: bool = False
) -> tuple[list[str], list[str], dict[str, int]]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = strip_comments(raw)
    blockers: list[str] = []
    warnings: list[str] = []
    counts: dict[str, int] = {}

    for name, pattern in UNRESOLVED_PATTERNS.items():
        for match in pattern.finditer(text):
            blockers.append(f"{path}:{line_number(text, match.start())}: {name}")

    for name, pattern in STYLE_PATTERNS.items():
        for match in pattern.finditer(text):
            warnings.append(f"{path}:{line_number(text, match.start())}: {name}: {match.group(0)!r}")

    for env in COUNTED_ENVIRONMENTS:
        starts = list(re.finditer(rf"\\begin\{{{env}\}}", text))
        ends = list(re.finditer(rf"\\end\{{{env}\}}", text))
        counts[env] = len(starts)
        if len(starts) != len(ends):
            blockers.append(
                f"{path}: unbalanced {env} environments ({len(starts)} begin, {len(ends)} end)"
            )

    for env in ("observation", "insight"):
        pattern = re.compile(
            rf"\\begin\{{{env}\}}(?:\[([^\]]*)\])?(.*?)\\end\{{{env}\}}",
            re.DOTALL,
        )
        for match in pattern.finditer(text):
            title, body = match.group(1) or "", match.group(2)
            if "\\label{" not in body:
                warnings.append(
                    f"{path}:{line_number(text, match.start())}: {env} has no label"
                )
            body_words = word_count(body)
            if body_words > MAX_CALLOUT_WORDS:
                blockers.append(
                    f"{path}:{line_number(text, match.start())}: {env} callout has "
                    f"{body_words} prose words; limit is {MAX_CALLOUT_WORDS}"
                )
            title_words = word_count(title)
            if title_words > MAX_CALLOUT_TITLE_WORDS:
                warnings.append(
                    f"{path}:{line_number(text, match.start())}: {env} title has "
                    f"{title_words} words; target at most {MAX_CALLOUT_TITLE_WORDS}"
                )
            sentence_count = len(re.findall(r"[.!?](?=\s|$)", prose_text(body)))
            if sentence_count > 2:
                blockers.append(
                    f"{path}:{line_number(text, match.start())}: {env} callout has "
                    f"{sentence_count} sentences; limit is 2"
                )
            if env == "insight":
                for part_name, part in (("title", title), ("body", body)):
                    if INSIGHT_IMPERATIVE_START.match(prose_text(part)):
                        blockers.append(
                            f"{path}:{line_number(text, match.start())}: insight "
                            f"{part_name} appears prescriptive; an Insight must be "
                            "a declarative claim, while prescriptions belong to a "
                            "Design principle"
                        )

    for env in FORMAL_RESULTS:
        pattern = re.compile(
            rf"\\begin\{{{env}\}}(?:\[[^\]]*\])?(.*?)\\end\{{{env}\}}",
            re.DOTALL,
        )
        for match in pattern.finditer(text):
            if "\\label{" not in match.group(1):
                warnings.append(
                    f"{path}:{line_number(text, match.start())}: {env} has no label"
                )

            proof_match = re.search(
                r"\\begin\{proof\}.*?\\end\{proof\}",
                text[match.end() : match.end() + 3000],
                re.DOTALL,
            )
            explanation_start = match.end()
            if proof_match:
                explanation_start = match.end() + proof_match.end()
            explanation_window = text[explanation_start : explanation_start + 1200]
            has_explanation_cue = bool(
                re.search(
                    r"\\paragraph\{Intuition\.\}|\\textit\{Intuition\.\}|"
                    r"\bIntuitively,|"
                    r"\bThe (?:result|lemma|proposition|identity|decomposition) "
                    r"(?:has|admits|offers|reveals|shows|means|separates)|"
                    r"\bEquation~?\\(?:eqref|ref)\{[^}]+\} "
                    r"(?:has|reveals|shows|means|separates)",
                    explanation_window,
                    re.IGNORECASE,
                )
            )
            if check_formal_explanation and not has_explanation_cue:
                warnings.append(
                    f"{path}:{line_number(text, match.start())}: {env} has no "
                    "nearby reader-explanation cue; inspect manually because "
                    "seamless explanations may not match this heuristic"
                )

    display_pattern = re.compile(
        r"\\begin\{(?:equation\*?|align\*?|gather\*?|multline\*?)\}",
    )
    counts["display_math"] = len(display_pattern.findall(text))

    return blockers, warnings, counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Main .tex file or paper directory")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return nonzero for warnings as well as blockers",
    )
    parser.add_argument(
        "--require-observation",
        type=int,
        default=0,
        metavar="N",
        help="Require at least N observation environments",
    )
    parser.add_argument(
        "--require-insight",
        type=int,
        default=0,
        metavar="N",
        help="Require at least N insight environments",
    )
    parser.add_argument(
        "--require-formal-result",
        type=int,
        default=0,
        metavar="N",
        help="Require at least N lemma/proposition/theorem/corollary environments",
    )
    parser.add_argument(
        "--require-proof",
        type=int,
        default=0,
        metavar="N",
        help="Require at least N local proof environments",
    )
    parser.add_argument(
        "--check-formal-explanation",
        action="store_true",
        help=(
            "Heuristically warn when a formal result lacks a nearby "
            "reader-facing explanation; manual review remains authoritative"
        ),
    )
    parser.add_argument(
        "--max-display-math",
        type=int,
        default=None,
        metavar="N",
        help="Fail if the audited source contains more than N display environments",
    )
    args = parser.parse_args()

    files = tex_files(args.path)
    if not files:
        print(f"No .tex files found under {args.path}", file=sys.stderr)
        return 2

    blockers: list[str] = []
    warnings: list[str] = []
    totals = {name: 0 for name in COUNTED_ENVIRONMENTS + ("display_math",)}

    for path in files:
        file_blockers, file_warnings, counts = findings_for_file(
            path, check_formal_explanation=args.check_formal_explanation
        )
        blockers.extend(file_blockers)
        warnings.extend(file_warnings)
        for name, count in counts.items():
            totals[name] += count

    requirements = {
        "observation": args.require_observation,
        "insight": args.require_insight,
    }
    for name, minimum in requirements.items():
        if totals[name] < minimum:
            blockers.append(
                f"callout gate: required at least {minimum} {name} environment(s), "
                f"found {totals[name]}"
            )

    formal_total = sum(totals[name] for name in FORMAL_RESULTS)
    if formal_total < args.require_formal_result:
        blockers.append(
            "formal-result gate: required at least "
            f"{args.require_formal_result} formal result environment(s), "
            f"found {formal_total}"
        )
    if totals["proof"] < args.require_proof:
        blockers.append(
            f"proof gate: required at least {args.require_proof} local proof "
            f"environment(s), found {totals['proof']}"
        )
    if formal_total > totals["proof"]:
        warnings.append(
            "formal results outnumber proof environments; verify that every result "
            "without a local proof explicitly points to a complete proof"
        )
    if args.max_display_math is not None and totals["display_math"] > args.max_display_math:
        blockers.append(
            f"equation-density gate: allowed at most {args.max_display_math} display "
            f"environment(s), found {totals['display_math']}"
        )

    print(f"Checked {len(files)} LaTeX file(s).")
    print(
        "Environments: "
        + ", ".join(f"{name}={count}" for name, count in totals.items())
    )

    if blockers:
        print("\nBlockers:")
        for item in blockers:
            print(f"- {item}")

    if warnings:
        print("\nWarnings requiring judgment:")
        for item in warnings:
            print(f"- {item}")

    if not blockers and not warnings:
        print("No deterministic issues found.")

    return 1 if blockers or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
