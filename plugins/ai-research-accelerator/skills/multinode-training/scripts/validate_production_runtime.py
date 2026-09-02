#!/usr/bin/env python3
"""Validate that a launch candidate contains the accepted production runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class ValidationError(RuntimeError):
    pass


def git(repo: Path, *args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=text,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() if text else result.stderr.decode().strip()
        raise ValidationError(f"git {' '.join(args)} failed: {stderr}")
    return result.stdout


def require_commit(repo: Path, value: Any, field: str) -> str:
    if not isinstance(value, str) or not COMMIT_RE.fullmatch(value):
        raise ValidationError(f"{field} must be a full 40-character lowercase commit")
    git(repo, "cat-file", "-e", f"{value}^{{commit}}")
    return value


def require_ancestor(repo: Path, ancestor: str, descendant: str, field: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", ancestor, descendant],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 1:
        raise ValidationError(f"{field} {ancestor} is not an ancestor of {descendant}")
    if result.returncode != 0:
        raise ValidationError(result.stderr.strip() or f"cannot compare {field}")


def object_bytes(repo: Path, commit: str, path: str) -> bytes:
    if not path or path.startswith("/") or ".." in Path(path).parts:
        raise ValidationError(f"repository path must be relative and normalized: {path!r}")
    return git(repo, "show", f"{commit}:{path}", text=False)


def require_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValidationError(f"{field} must be a non-empty string list")
    return value


def validate(
    manifest: dict[str, Any],
    *,
    repo: Path,
    profile_id: str,
    candidate: str,
    require_clean: bool,
) -> dict[str, Any]:
    if manifest.get("schema_version") != 1:
        raise ValidationError("schema_version must be 1")
    runtime_id = manifest.get("runtime_id")
    if not isinstance(runtime_id, str) or not runtime_id:
        raise ValidationError("runtime_id must be a non-empty string")

    candidate = require_commit(repo, candidate, "candidate_commit")
    canonical = require_commit(
        repo, manifest.get("canonical_runtime_commit"), "canonical_runtime_commit"
    )
    require_ancestor(repo, canonical, candidate, "canonical_runtime_commit")

    accepted = manifest.get("accepted_runtime")
    if not isinstance(accepted, dict):
        raise ValidationError("accepted_runtime must be an object")
    require_commit(repo, accepted.get("commit"), "accepted_runtime.commit")
    require_string_list(accepted.get("evidence_paths"), "accepted_runtime.evidence_paths")

    fixes_raw = manifest.get("fixes")
    if not isinstance(fixes_raw, list):
        raise ValidationError("fixes must be a list")
    fixes: dict[str, dict[str, Any]] = {}
    for index, fix in enumerate(fixes_raw):
        if not isinstance(fix, dict):
            raise ValidationError(f"fixes[{index}] must be an object")
        fix_id = fix.get("id")
        if not isinstance(fix_id, str) or not fix_id or fix_id in fixes:
            raise ValidationError(f"fixes[{index}].id must be unique and non-empty")
        require_string_list(
            fix.get("required_for_profiles"),
            f"fixes[{fix_id}].required_for_profiles",
        )
        fixes[fix_id] = fix

    profiles_raw = manifest.get("profiles")
    if not isinstance(profiles_raw, list):
        raise ValidationError("profiles must be a list")
    matches = [item for item in profiles_raw if isinstance(item, dict) and item.get("id") == profile_id]
    if len(matches) != 1:
        raise ValidationError(f"profile {profile_id!r} must appear exactly once")
    profile = matches[0]
    profile_base = require_commit(
        repo, profile.get("production_base_commit"), "profile.production_base_commit"
    )
    if profile_base != canonical:
        raise ValidationError("profile.production_base_commit must equal canonical_runtime_commit")
    required_ids = set(
        require_string_list(profile.get("required_fix_ids"), "profile.required_fix_ids")
    )
    applicable_ids = {
        fix_id
        for fix_id, fix in fixes.items()
        if profile_id in fix.get("required_for_profiles", [])
        or "*" in fix.get("required_for_profiles", [])
    }
    missing_declarations = applicable_ids - required_ids
    if missing_declarations:
        raise ValidationError(
            "profile omits applicable fixes: " + ", ".join(sorted(missing_declarations))
        )

    validated_fixes: list[str] = []
    for fix_id in sorted(required_ids):
        fix = fixes.get(fix_id)
        if fix is None:
            raise ValidationError(f"profile requires unknown fix {fix_id!r}")
        if fix.get("status") != "promoted":
            raise ValidationError(f"fix {fix_id!r} is not promoted")
        promoted_commit = require_commit(
            repo, fix.get("promoted_commit"), f"fixes[{fix_id}].promoted_commit"
        )
        require_ancestor(repo, promoted_commit, candidate, f"fix {fix_id!r}")
        require_string_list(fix.get("source_evidence_paths"), f"fixes[{fix_id}].source_evidence_paths")
        tests = require_string_list(fix.get("regression_tests"), f"fixes[{fix_id}].regression_tests")
        for test_path in tests:
            object_bytes(repo, candidate, test_path)
        validated_fixes.append(fix_id)

    contract_path = profile.get("science_contract_path")
    if not isinstance(contract_path, str) or not contract_path:
        raise ValidationError("profile.science_contract_path must be non-empty")
    expected_hash = profile.get("science_contract_sha256")
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise ValidationError("profile.science_contract_sha256 must be lowercase SHA256")
    actual_hash = hashlib.sha256(object_bytes(repo, candidate, contract_path)).hexdigest()
    if actual_hash != expected_hash:
        raise ValidationError(
            f"science contract hash mismatch: expected {expected_hash}, got {actual_hash}"
        )

    if require_clean and git(repo, "status", "--porcelain").strip():
        raise ValidationError("repository must be clean")

    return {
        "accepted": True,
        "runtime_id": runtime_id,
        "profile_id": profile_id,
        "candidate_commit": candidate,
        "canonical_runtime_commit": canonical,
        "validated_fix_ids": validated_fixes,
        "science_contract_sha256": actual_hash,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--candidate-commit", default="HEAD")
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text())
        candidate = str(git(args.repo, "rev-parse", args.candidate_commit)).strip()
        result = validate(
            manifest,
            repo=args.repo,
            profile_id=args.profile,
            candidate=candidate,
            require_clean=args.require_clean,
        )
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(json.dumps({"accepted": False, "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
