#!/usr/bin/env python3
"""Read-only consistency audit for Markdown paper experiment ledgers."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


ID_RE = re.compile(r"\bP[1-3](?:-[A-Z0-9]+)+-V\d+-A\d+\b")
RUN_RE = re.compile(r"https?://[^\s)>]+?/runs/([a-z0-9]+)", re.IGNORECASE)
SHA_RE = re.compile(r"\b[0-9a-f]{40}\b", re.IGNORECASE)
HOST_RE = re.compile(
    r"(?:\bhost(?:name)?\s*[:=]\s*[a-z0-9.-]+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.kwaidc\.com\b|\bge\d{3}-\d+\b)",
    re.IGNORECASE,
)
WANDB_NAME_RE = re.compile(
    r"(?:W&B|wandb)\s*(?:display\s*)?name\s*[:=]",
    re.IGNORECASE,
)

REQUIRED_SECTIONS = {
    "plan coverage matrix": ("覆盖矩阵",),
    "paper result lookup": ("论文结果速查",),
    "historical evidence index": ("历史机制证据索引",),
}

ACTIVE = {"reserved", "queued", "running", "evaluating", "已预留", "已排队", "运行中", "评测中"}
COMPLETE = {
    "complete-formal",
    "complete-baseline",
    "complete-historical",
    "complete-valid-collapse",
    "完成-正式",
    "完成-基线",
    "完成-历史",
    "完成-有效崩溃",
    "完成-ra",
}
KNOWN = ACTIVE | COMPLETE | {
    "not-started",
    "cancelled",
    "invalid-config",
    "failed-infrastructure",
    "failed-discarded",
    "未开始",
    "已取消",
    "配置无效",
    "基础设施失败",
    "失败-弃用",
    "可选-未启动",
    "无效-配置",
}


@dataclass(frozen=True)
class Record:
    line: int
    experiment_id: str
    status: str | None
    run_ids: tuple[str, ...]
    has_full_sha: bool
    has_host: bool
    has_best: bool
    has_final: bool
    has_checkpoint: bool
    has_wandb_name: bool
    text: str


def split_markdown_row(line: str) -> list[str]:
    return [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]


def status_from_cells(cells: list[str]) -> str | None:
    for cell in cells:
        normalized = cell.strip().lower().replace(" ", "-")
        if normalized in KNOWN:
            return normalized
    joined = " ".join(cells).lower()
    for status in sorted(KNOWN, key=len, reverse=True):
        if status.lower() in joined:
            return status.lower()
    return None


def parse_records(text: str) -> list[Record]:
    records: list[Record] = []
    for number, line in enumerate(text.splitlines(), 1):
        if "|" not in line:
            continue
        ids = ID_RE.findall(line)
        if not ids:
            continue
        cells = split_markdown_row(line)
        lower = line.lower()
        for experiment_id in sorted(set(ids)):
            records.append(
                Record(
                    line=number,
                    experiment_id=experiment_id,
                    status=status_from_cells(cells),
                    run_ids=tuple(sorted(set(RUN_RE.findall(line)))),
                    has_full_sha=bool(SHA_RE.search(line)),
                    has_host=bool(HOST_RE.search(line)),
                    has_best="best" in lower or "最佳" in line,
                    has_final="final" in lower or "最终" in line,
                    has_checkpoint="checkpoint" in lower or "ckpt" in lower or "检查点" in line,
                    has_wandb_name=bool(WANDB_NAME_RE.search(line)),
                    text=line.strip(),
                )
            )
    return records


def section_body(text: str, heading_fragment: str) -> str | None:
    lines = text.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if line.startswith("## ") and heading_fragment in line),
        None,
    )
    if start is None:
        return None
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[start + 1 : end])


def audit_document(text: str) -> tuple[list[str], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    bodies: dict[str, str] = {}
    for label, fragments in REQUIRED_SECTIONS.items():
        body = next((section_body(text, fragment) for fragment in fragments if section_body(text, fragment)), None)
        if body is None:
            errors.append(f"missing required paper-wide ledger section: {label}")
            continue
        bodies[label] = body
        data_rows = [
            line
            for line in body.splitlines()
            if line.startswith("|")
            and not re.match(r"^\|[\s|:-]+$", line)
            and not any(
                token in line
                for token in (
                    "plan.md` 项目",
                    "Model/benchmark",
                    "证据主题",
                )
            )
        ]
        if not data_rows:
            errors.append(f"required ledger section has no data rows: {label}")
        else:
            info.append(f"{label}: {len(data_rows)} data rows")

    historical = bodies.get("historical evidence index")
    if historical is not None:
        for line_number, line in enumerate(historical.splitlines(), 1):
            if not line.startswith("|") or re.match(r"^\|[\s|:-]+$", line):
                continue
            if "证据主题" in line:
                continue
            has_link = bool(RUN_RE.search(line))
            explains_absence = any(
                marker in line.lower()
                for marker in ("无 wandb link", "no wandb link", "无 w&b link", "offline")
            )
            if not has_link and not explains_absence:
                warnings.append(
                    "historical evidence row lacks a W&B run URL or an explicit no-link explanation: "
                    f"section row {line_number}"
                )

    return errors, warnings, info


def audit(
    records: list[Record],
    *,
    require_wandb_names: bool = False,
    named_run_ids: set[str] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []
    named_run_ids = named_run_ids or set()
    by_id: dict[str, list[Record]] = defaultdict(list)
    by_run: dict[str, set[str]] = defaultdict(set)

    for record in records:
        by_id[record.experiment_id].append(record)
        for run_id in record.run_ids:
            by_run[run_id].add(record.experiment_id)

    for run_id, experiment_ids in sorted(by_run.items()):
        if len(experiment_ids) > 1:
            training_ids = {experiment_id for experiment_id in experiment_ids if "-BASE-" not in experiment_id}
            if len(training_ids) > 1:
                errors.append(
                    f"W&B run {run_id} is assigned to multiple training experiment IDs: "
                    f"{', '.join(sorted(experiment_ids))}"
                )
            else:
                info.append(
                    f"W&B run {run_id} is shared by a training attempt and derived BASE evaluation: "
                    f"{', '.join(sorted(experiment_ids))}"
                )

    for experiment_id, rows in sorted(by_id.items()):
        statuses = {row.status for row in rows if row.status is not None}
        active_statuses = statuses & ACTIVE
        terminal_statuses = statuses & COMPLETE
        running = bool(statuses & {"running", "evaluating", "运行中", "评测中"})
        formal = bool(statuses & {"complete-formal", "完成-正式"})
        completed = bool(terminal_statuses)
        derived_base = "-BASE-" in experiment_id
        smoke = "-a0" in experiment_id.lower() or any("smoke" in row.text.lower() for row in rows)
        run_ids = {run_id for row in rows for run_id in row.run_ids}
        has_host = any(row.has_host for row in rows)
        has_full_sha = any(row.has_full_sha for row in rows)
        has_best = any(row.has_best for row in rows)
        has_final = any(row.has_final for row in rows)
        has_checkpoint = any(row.has_checkpoint for row in rows)
        has_wandb_name = any(row.has_wandb_name for row in rows) or (
            bool(run_ids) and run_ids.issubset(named_run_ids)
        )

        if running and not run_ids and not derived_base:
            errors.append(f"{experiment_id}: running/evaluating but no W&B run URL appears in any ledger row")
        if active_statuses and not has_host:
            warnings.append(f"{experiment_id}: active but no hostname appears in any ledger row")
        if active_statuses and not has_full_sha:
            warnings.append(f"{experiment_id}: active but no full 40-char SHA appears in any ledger row")
        if completed and not run_ids and not derived_base:
            warnings.append(f"{experiment_id}: completed but no W&B run URL appears in any ledger row")
        if require_wandb_names and run_ids and (active_statuses or completed) and not has_wandb_name:
            warnings.append(
                f"{experiment_id}: W&B run exists but exact display name is not recorded as `W&B name=...`"
            )
        if formal and not smoke and not derived_base:
            if not has_final:
                warnings.append(f"{experiment_id}: formal completion does not mention final evaluation")
            if not has_best:
                warnings.append(f"{experiment_id}: formal completion does not mention best evaluation")
            if not has_checkpoint:
                warnings.append(f"{experiment_id}: formal completion does not mention a checkpoint")
        if any(
            row.status in {"running", "evaluating", "运行中", "评测中"} | COMPLETE
            and any(token in row.text for token in ("TODO", "TBD", "待生成", "待确认"))
            for row in rows
        ):
            warnings.append(f"{experiment_id}: running/completed record still contains a placeholder")

        if active_statuses and terminal_statuses:
            warnings.append(
                f"{experiment_id} appears in both active and terminal states: {', '.join(sorted(statuses))}"
            )
        if len(rows) > 1:
            info.append(f"{experiment_id} appears in {len(rows)} ledger rows; verify overview/detail rows agree")

    return errors, warnings, info


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path, help="Markdown experiment ledger")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON")
    parser.add_argument("--strict", action="store_true", help="return nonzero when warnings exist")
    parser.add_argument(
        "--require-wandb-names",
        action="store_true",
        help="warn when active/completed W&B runs lack an explicit display name",
    )
    args = parser.parse_args()

    if not args.ledger.is_file():
        print(f"error: ledger not found: {args.ledger}", file=sys.stderr)
        return 2

    text = args.ledger.read_text(encoding="utf-8")
    records = parse_records(text)
    named_run_ids = {
        run_id
        for line in text.splitlines()
        if WANDB_NAME_RE.search(line)
        for run_id in RUN_RE.findall(line)
    }
    errors, warnings, info = audit(
        records,
        require_wandb_names=args.require_wandb_names,
        named_run_ids=named_run_ids,
    )
    doc_errors, doc_warnings, doc_info = audit_document(text)
    errors.extend(doc_errors)
    warnings.extend(doc_warnings)
    info.extend(doc_info)
    payload = {
        "ledger": str(args.ledger.resolve()),
        "records": len(records),
        "unique_experiments": len({record.experiment_id for record in records}),
        "errors": errors,
        "warnings": warnings,
        "info": info,
    }

    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Ledger: {payload['ledger']}")
        print(f"Parsed: {payload['records']} rows, {payload['unique_experiments']} unique experiment IDs")
        for label, items in (("ERROR", errors), ("WARN", warnings), ("INFO", info)):
            for item in items:
                print(f"{label}: {item}")
        if not errors and not warnings:
            print("OK: no consistency issues detected")

    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
