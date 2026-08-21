#!/usr/bin/env python3
"""Check structural label alignment between English and Chinese paper sources."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path


LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
MARKER_RE = re.compile(r"<!--\s*SYNC:\s*([^\s]+)\s*-->")


def duplicates(items: list[str]) -> list[str]:
    return sorted(item for item, count in Counter(items).items() if count > 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("english", type=Path, help="English LaTeX source")
    parser.add_argument("chinese", type=Path, help="Chinese LaTeX or Markdown mirror")
    args = parser.parse_args()

    english_labels = LABEL_RE.findall(args.english.read_text(encoding="utf-8"))
    chinese_text = args.chinese.read_text(encoding="utf-8")
    chinese_markers = (
        LABEL_RE.findall(chinese_text)
        if args.chinese.suffix.lower() == ".tex"
        else MARKER_RE.findall(chinese_text)
    )

    missing = [label for label in english_labels if label not in chinese_markers]
    extra = [label for label in chinese_markers if label not in english_labels]
    duplicate_labels = duplicates(english_labels)
    duplicate_markers = duplicates(chinese_markers)
    shared_markers = [label for label in chinese_markers if label in english_labels]
    order_matches = shared_markers == [
        label for label in english_labels if label in chinese_markers
    ]

    print(f"English labels: {len(english_labels)}")
    print(f"Chinese structural markers: {len(chinese_markers)}")
    if missing:
        print("Missing markers: " + ", ".join(missing))
    if extra:
        print("Unknown markers: " + ", ".join(extra))
    if duplicate_labels:
        print("Duplicate English labels: " + ", ".join(duplicate_labels))
    if duplicate_markers:
        print("Duplicate Chinese markers: " + ", ".join(duplicate_markers))
    if not order_matches:
        print("Marker order differs from English label order")

    failed = bool(
        missing
        or extra
        or duplicate_labels
        or duplicate_markers
        or not order_matches
    )
    if not failed:
        print("Bilingual structural sync: pass")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
