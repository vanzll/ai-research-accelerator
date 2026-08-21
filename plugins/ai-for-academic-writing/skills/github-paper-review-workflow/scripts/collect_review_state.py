#!/usr/bin/env python3
"""Collect all human/AI review state for an academic-paper pull request.

The command is read-only and fails closed when review threads cannot be queried.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from typing import Any, Iterable


AI_MARKER_PREFIX = "<!-- academic-writing-ai:"
RESPONSE_RE = re.compile(
    r"<!--\s*academic-writing-ai:(?:response|status)\s+"
    r"source_id=([^\s>]+)(?:\s+commit=([^\s>]+))?\s*-->",
    re.IGNORECASE,
)


class ReviewAuditError(RuntimeError):
    pass


def run_gh(args: list[str], *, input_text: str | None = None) -> Any:
    proc = subprocess.run(
        ["gh", *args],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode:
        detail = proc.stderr.strip() or proc.stdout.strip()
        raise ReviewAuditError(f"gh {' '.join(args)} failed: {detail}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ReviewAuditError(f"gh returned invalid JSON: {exc}") from exc


def is_ai_message(body: str | None) -> bool:
    return AI_MARKER_PREFIX in (body or "").lower()


def linked_source_ids(body: str | None) -> set[str]:
    return {match.group(1) for match in RESPONSE_RE.finditer(body or "")}


def iso_key(value: str | None) -> str:
    return value or ""


def actor_login(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("login")
    return None


def normalize_message(
    *,
    source: str,
    node: dict[str, Any],
    thread: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = node.get("body") or ""
    node_id = str(node.get("id") or node.get("databaseId") or "")
    return {
        "source": source,
        "id": node_id,
        "database_id": node.get("databaseId"),
        "thread_id": (thread or {}).get("id"),
        "thread_resolved": (thread or {}).get("isResolved"),
        "thread_outdated": (thread or {}).get("isOutdated"),
        "path": (thread or {}).get("path") or node.get("path"),
        "line": (thread or {}).get("line") or node.get("line"),
        "original_line": (thread or {}).get("originalLine") or node.get("originalLine"),
        "author": actor_login(node.get("author") or node.get("user")),
        "body": body,
        "created_at": node.get("createdAt") or node.get("created_at"),
        "updated_at": node.get("updatedAt") or node.get("updated_at"),
        "url": node.get("url") or node.get("html_url"),
        "ai_marked": is_ai_message(body),
        "linked_source_ids": sorted(linked_source_ids(body)),
    }


def classify_messages(
    messages: Iterable[dict[str, Any]], authorized_authors: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    human: list[dict[str, Any]] = []
    ai: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    for message in messages:
        if message["ai_marked"]:
            ai.append(message)
        elif message.get("author") in authorized_authors:
            human.append(message)
        else:
            ignored.append(message)

    responses: dict[str, list[dict[str, Any]]] = {}
    for message in ai:
        for source_id in message["linked_source_ids"]:
            responses.setdefault(source_id, []).append(message)

    for message in human:
        later = [
            response
            for response in responses.get(message["id"], [])
            if iso_key(response.get("created_at")) >= iso_key(message.get("created_at"))
        ]
        message["addressed_by_ai"] = bool(later)
        message["ai_responses"] = [response["id"] for response in later]

    human.sort(key=lambda item: iso_key(item.get("created_at")))
    return human, ai, ignored


def fetch_threads(repo: str, pr_number: int) -> list[dict[str, Any]]:
    owner, name = repo.split("/", 1)
    query = """
query($owner:String!,$name:String!,$number:Int!,$cursor:String) {
  repository(owner:$owner,name:$name) {
    pullRequest(number:$number) {
      reviewThreads(first:100,after:$cursor) {
        nodes {
          id isResolved isOutdated path line originalLine
          comments(first:100) {
            nodes { id databaseId body createdAt updatedAt url author { login } path line originalLine }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""
    threads: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        args = [
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={name}",
            "-F",
            f"number={pr_number}",
        ]
        if cursor:
            args.extend(["-F", f"cursor={cursor}"])
        data = run_gh(args)
        try:
            connection = data["data"]["repository"]["pullRequest"]["reviewThreads"]
        except (KeyError, TypeError) as exc:
            raise ReviewAuditError("GitHub did not return review-thread state") from exc
        threads.extend(connection.get("nodes") or [])
        page = connection["pageInfo"]
        if not page["hasNextPage"]:
            return threads
        cursor = page["endCursor"]


def check_summary(status_rollup: list[dict[str, Any]] | None) -> dict[str, Any]:
    checks = status_rollup or []
    accepted = {"SUCCESS", "NEUTRAL", "SKIPPED"}
    blockers = []
    for check in checks:
        state = check.get("conclusion") or check.get("state") or check.get("status")
        if state not in accepted:
            blockers.append({"name": check.get("name") or check.get("context"), "state": state})
    return {"green": not blockers, "blockers": blockers, "count": len(checks)}


def collect(repo: str | None, pr: str | None, authors: list[str], allow_public: bool) -> dict[str, Any]:
    repo_info = run_gh(["repo", "view", *( [repo] if repo else [] ), "--json", "nameWithOwner,visibility,isPrivate,url"])
    repo_name = repo_info["nameWithOwner"]
    if not repo_info.get("isPrivate") and not allow_public:
        raise ReviewAuditError(
            f"repository {repo_name} is {repo_info.get('visibility')}; pass --allow-public only with explicit author approval"
        )

    current_login = run_gh(["api", "user"])["login"]
    authorized = set(authors or [current_login])
    pr_args = ["pr", "view"]
    if pr:
        pr_args.append(pr)
    pr_args.extend(
        [
            "--repo",
            repo_name,
            "--json",
            "number,url,title,state,isDraft,headRefName,baseRefName,author,reviewDecision,reviews,comments,statusCheckRollup",
        ]
    )
    pr_data = run_gh(pr_args)
    threads = fetch_threads(repo_name, int(pr_data["number"]))

    messages: list[dict[str, Any]] = []
    for comment in pr_data.get("comments") or []:
        messages.append(normalize_message(source="issue_comment", node=comment))
    for review in pr_data.get("reviews") or []:
        if (review.get("body") or "").strip():
            messages.append(normalize_message(source="review_summary", node=review))
    for thread in threads:
        for comment in (thread.get("comments") or {}).get("nodes") or []:
            messages.append(normalize_message(source="review_thread", node=comment, thread=thread))

    human, ai, ignored = classify_messages(messages, authorized)
    active_human = [item for item in human if not item.get("addressed_by_ai")]
    unresolved_human_threads = sorted(
        {
            item["thread_id"]
            for item in human
            if item.get("thread_id") and item.get("thread_resolved") is False
        }
    )
    checks = check_summary(pr_data.get("statusCheckRollup"))
    merge_gate = {
        "ready": False,
        "unaddressed_human_instructions": len(active_human),
        "unresolved_human_threads": len(unresolved_human_threads),
        "checks_green": checks["green"],
        "explicit_author_approval_required": True,
    }
    return {
        "schema_version": 1,
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repository": repo_info,
        "pull_request": {
            key: pr_data.get(key)
            for key in (
                "number",
                "url",
                "title",
                "state",
                "isDraft",
                "headRefName",
                "baseRefName",
                "reviewDecision",
            )
        },
        "authorized_authors": sorted(authorized),
        "ai_marker_prefix": AI_MARKER_PREFIX,
        "human_instructions": human,
        "active_human_instructions": active_human,
        "ai_messages": ai,
        "ignored_unmarked_messages": ignored,
        "unresolved_human_thread_ids": unresolved_human_threads,
        "checks": checks,
        "merge_gate": merge_gate,
    }


def render_markdown(data: dict[str, Any]) -> str:
    pr = data["pull_request"]
    gate = data["merge_gate"]
    lines = [
        f"# Review audit: {data['repository']['nameWithOwner']}#{pr['number']}",
        "",
        f"- PR: {pr['url']}",
        f"- Visibility: {data['repository']['visibility']}",
        f"- Authorized authors: {', '.join(data['authorized_authors'])}",
        f"- Active human instructions: {gate['unaddressed_human_instructions']}",
        f"- Unresolved human threads: {gate['unresolved_human_threads']}",
        f"- Checks green: {gate['checks_green']}",
        "- Explicit author approval: required",
        "",
        "## Active author instructions",
    ]
    active = data["active_human_instructions"]
    if not active:
        lines.append("None.")
    for item in active:
        location = item.get("path") or item["source"]
        if item.get("line"):
            location += f":{item['line']}"
        lines.extend(
            [
                "",
                f"- `{item['id']}` by `{item['author']}` at {location}",
                f"  {item.get('url') or ''}",
                "",
                "  " + item["body"].strip().replace("\n", "\n  "),
            ]
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="OWNER/REPO; inferred from the current checkout by default")
    parser.add_argument("--pr", help="pull-request number or URL; inferred from the current branch by default")
    parser.add_argument("--author-login", action="append", default=[], help="authorized human author login; repeatable")
    parser.add_argument("--allow-public", action="store_true", help="allow auditing a public repository after explicit approval")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", help="write output to a file instead of stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = collect(args.repo, args.pr, args.author_login, args.allow_public)
    except ReviewAuditError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rendered = render_markdown(result) if args.format == "markdown" else json.dumps(result, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            if not rendered.endswith("\n"):
                handle.write("\n")
    else:
        print(rendered, end="" if rendered.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
