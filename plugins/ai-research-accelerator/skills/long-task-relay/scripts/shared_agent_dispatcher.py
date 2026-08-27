#!/usr/bin/env python3
"""Shared-filesystem request bus for coordinator and worker Codex sessions."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import glob
import json
import os
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
DEFAULT_INSTANCE_ID = "foreground"
DEFAULT_AGENT_MODE = "fresh"
AGENT_MODES = {"fresh", "resume"}
TERMINAL_RESULT_STATES = {"succeeded", "failed", "needs_coordinator"}
ACTIVE_DISPATCHER_STATES = {
    "waiting-for-manifest",
    "waiting-for-active-attempt",
    "waiting-for-next-attempt",
    "watching",
    "waiting-for-thread-idle",
    "agent-active",
    "restarting",
}
_BACKGROUND_PROCESSES: dict[int, subprocess.Popen[str]] = {}


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def short_hostname() -> str:
    return socket.gethostname().split(".", 1)[0]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _write_temporary(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return temporary


def atomic_replace_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = _write_temporary(path, payload)
    os.replace(temporary, path)


def atomic_create_json(path: Path, payload: dict[str, Any]) -> bool:
    """Atomically publish an immutable JSON record without overwriting a peer."""
    temporary = _write_temporary(path, payload)
    try:
        os.link(temporary, path)
    except FileExistsError:
        return False
    finally:
        temporary.unlink(missing_ok=True)
    return True


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    owned = _BACKGROUND_PROCESSES.get(pid)
    if owned is not None:
        if owned.poll() is None:
            return True
        _BACKGROUND_PROCESSES.pop(pid, None)
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def process_start_token(pid: int) -> str | None:
    proc_stat = Path(f"/proc/{pid}/stat")
    if proc_stat.exists():
        try:
            fields = proc_stat.read_text(encoding="utf-8").rsplit(")", 1)[1].split()
            return f"proc:{fields[19]}"
        except (OSError, IndexError):
            return None
    try:
        completed = subprocess.run(
            ["ps", "-o", "lstart=", "-p", str(pid)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    value = completed.stdout.strip()
    return f"ps:{value}" if completed.returncode == 0 and value else None


def process_argv(pid: int) -> list[str]:
    proc_cmdline = Path(f"/proc/{pid}/cmdline")
    if proc_cmdline.exists():
        try:
            return [
                value.decode("utf-8", errors="replace")
                for value in proc_cmdline.read_bytes().split(b"\0")
                if value
            ]
        except OSError:
            return []
    if not process_alive(pid):
        return []
    try:
        completed = subprocess.run(
            ["ps", "-o", "command=", "-p", str(pid)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    command = completed.stdout.strip()
    try:
        return shlex.split(command)
    except ValueError:
        return []


def option_value(argv: list[str], option: str) -> str | None:
    try:
        return argv[argv.index(option) + 1]
    except (ValueError, IndexError):
        return None


def option_value_or_default(
    argv: list[str], option: str, default: str
) -> str:
    value = option_value(argv, option)
    return default if value is None else value


def dispatcher_process_matches(state: dict[str, Any], root: Path, node: str) -> bool:
    pid = int(state.get("pid", -1))
    if not process_alive(pid):
        return False
    if process_start_token(pid) != state.get("process_start_token"):
        return False
    argv = process_argv(pid)
    return (
        any(Path(value).name == "shared_agent_dispatcher.py" for value in argv)
        and option_value(argv, "--root") == str(root)
        and option_value(argv, "--node") == node
        and option_value_or_default(
            argv, "--instance-id", DEFAULT_INSTANCE_ID
        )
        == state.get("instance_id")
    )


def manifest_path(root: Path) -> Path:
    return root / "agent-bus-manifest.json"


def load_manifest(root: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path(root))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported agent-bus manifest schema")
    required = {
        "experiment_id",
        "attempt",
        "launch_nonce",
        "science_contract_hash",
        "fencing_epoch",
        "coordinator_node",
        "coordinator_thread_id",
        "authority_root",
        "nodes",
    }
    missing = sorted(required - manifest.keys())
    if missing:
        raise ValueError(f"agent-bus manifest missing: {', '.join(missing)}")
    if not isinstance(manifest["nodes"], dict):
        raise ValueError("manifest nodes must be an object")
    return manifest


def campaign_manifest_path(root: Path) -> Path:
    return root / "campaign-manifest.json"


def campaign_active_attempt_path(root: Path) -> Path:
    return root / "active-attempt.json"


def campaign_goal_completed_path(root: Path) -> Path:
    return root / "goal-completed.json"


def campaign_binding_path(attempt_root: Path) -> Path:
    return attempt_root / "campaign-binding.json"


def load_campaign_manifest(root: Path) -> dict[str, Any]:
    manifest = read_json(campaign_manifest_path(root))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported agent campaign manifest schema")
    required = {
        "campaign_id",
        "science_contract_hash",
        "coordinator_node",
        "coordinator_hostname",
        "coordinator_thread_id",
        "authority_root",
        "attempts_root",
        "nodes",
    }
    missing = sorted(required - manifest.keys())
    if missing:
        raise ValueError(f"campaign manifest missing: {', '.join(missing)}")
    if not isinstance(manifest["nodes"], dict):
        raise ValueError("campaign nodes must be an object")
    return manifest


def parse_node(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("node must use NODE=HOSTNAME")
    node, hostname = value.split("=", 1)
    if not node.startswith("node") or not node[4:].isdigit() or not hostname:
        raise argparse.ArgumentTypeError("node must use nodeN=HOSTNAME")
    return node, hostname.split(".", 1)[0]


def initialize_bus(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    authority_root = Path(args.authority_root).expanduser().resolve()
    nodes = dict(args.node)
    if args.coordinator_node not in nodes:
        raise ValueError("coordinator node is missing from --node entries")
    expected_host = nodes[args.coordinator_node]
    if short_hostname() != expected_host and not args.allow_host_mismatch:
        raise ValueError(
            f"coordinator host mismatch: running on {short_hostname()}, expected {expected_host}"
        )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": args.experiment_id,
        "attempt": args.attempt,
        "launch_nonce": args.launch_nonce,
        "science_contract_hash": args.science_contract_hash,
        "fencing_epoch": args.fencing_epoch,
        "coordinator_node": args.coordinator_node,
        "coordinator_hostname": expected_host,
        "coordinator_thread_id": args.coordinator_thread_id,
        "authority_root": str(authority_root),
        "nodes": nodes,
        "created_at": timestamp(),
    }
    authority_root.mkdir(parents=True, exist_ok=True)
    lock_path = authority_root / "coordinator.lock"
    path = manifest_path(root)
    identity_keys = [
        "schema_version",
        "experiment_id",
        "attempt",
        "launch_nonce",
        "science_contract_hash",
        "fencing_epoch",
        "coordinator_node",
        "coordinator_hostname",
        "coordinator_thread_id",
        "authority_root",
        "nodes",
    ]
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        active_campaign_path = authority_root / "active-agent-campaign.json"
        if active_campaign_path.exists():
            active_campaign = read_json(active_campaign_path)
            campaign_root = Path(active_campaign["root"]).expanduser().resolve()
            campaign = load_campaign_manifest(campaign_root)
            if campaign_goal_completed_path(campaign_root).exists():
                raise ValueError("agent campaign is already completed")
            attempts_root = Path(campaign["attempts_root"]).expanduser().resolve()
            if not root.is_relative_to(attempts_root):
                raise ValueError("attempt root is outside the active campaign")
            candidate = {**payload, "authority_root": str(authority_root)}
            validate_attempt_for_campaign(campaign, candidate)
        active_path = authority_root / "active-agent-bus.json"
        active = read_json(active_path) if active_path.exists() else None
        active_payload = {
            "schema_version": SCHEMA_VERSION,
            "root": str(root),
            "experiment_id": args.experiment_id,
            "attempt": args.attempt,
            "launch_nonce": args.launch_nonce,
            "science_contract_hash": args.science_contract_hash,
            "fencing_epoch": args.fencing_epoch,
            "coordinator_node": args.coordinator_node,
            "coordinator_hostname": expected_host,
            "coordinator_thread_id": args.coordinator_thread_id,
            "updated_at": timestamp(),
        }
        if active is not None and active.get("root") != str(root):
            if args.fencing_epoch <= int(active.get("fencing_epoch", -1)):
                raise ValueError("new agent-bus fencing epoch must be strictly greater")
        if path.exists():
            existing = load_manifest(root)
            if any(existing.get(key) != payload.get(key) for key in identity_keys):
                raise ValueError(f"refusing to replace mismatched manifest: {path}")
        for node in nodes:
            for directory in ("inbox", "claims", "acks", "results", "invocations"):
                (root / directory / node).mkdir(parents=True, exist_ok=True)
        # Publish the complete immutable attempt before advancing authority.
        # A crash can leave an inert orphan attempt, never an active pointer to
        # a missing manifest.
        if not path.exists() and not atomic_create_json(path, payload):
            raise RuntimeError(f"failed to publish agent-bus manifest: {path}")
        atomic_replace_json(active_path, active_payload)
    print(path)
    return 0


def validate_attempt_for_campaign(
    campaign: dict[str, Any], attempt: dict[str, Any]
) -> None:
    expected = {
        "science_contract_hash": campaign["science_contract_hash"],
        "coordinator_node": campaign["coordinator_node"],
        "coordinator_hostname": campaign["coordinator_hostname"],
        "coordinator_thread_id": campaign["coordinator_thread_id"],
        "authority_root": campaign["authority_root"],
        "nodes": campaign["nodes"],
    }
    for key, value in expected.items():
        if attempt.get(key) != value:
            raise ValueError(f"attempt is outside campaign: {key} mismatch")


def validate_campaign_coordinator_identity(campaign: dict[str, Any]) -> None:
    coordinator = campaign["coordinator_node"]
    expected_host = campaign["nodes"].get(coordinator)
    if short_hostname() != expected_host:
        raise ValueError(
            f"coordinator host mismatch: running on {short_hostname()}, expected {expected_host}"
        )
    observed_thread = os.environ.get("CODEX_THREAD_ID")
    if observed_thread != campaign["coordinator_thread_id"]:
        raise ValueError(
            "coordinator thread mismatch: command is not from the frozen Node 0 Goal"
        )


def initialize_campaign(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    authority_root = Path(args.authority_root).expanduser().resolve()
    nodes = dict(args.node)
    if args.coordinator_node not in nodes:
        raise ValueError("coordinator node is missing from --node entries")
    expected_host = nodes[args.coordinator_node]
    if short_hostname() != expected_host and not args.allow_host_mismatch:
        raise ValueError(
            f"coordinator host mismatch: running on {short_hostname()}, expected {expected_host}"
        )
    if (
        os.environ.get("CODEX_THREAD_ID") != args.coordinator_thread_id
        and not args.allow_host_mismatch
    ):
        raise ValueError(
            "coordinator thread mismatch: campaign must be initialized by the frozen Node 0 Goal"
        )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": "agent-campaign-manifest",
        "campaign_id": args.campaign_id,
        "science_contract_hash": args.science_contract_hash,
        "coordinator_node": args.coordinator_node,
        "coordinator_hostname": expected_host,
        "coordinator_thread_id": args.coordinator_thread_id,
        "authority_root": str(authority_root),
        "attempts_root": str(Path(args.attempts_root).expanduser().resolve()),
        "nodes": nodes,
        "created_at": timestamp(),
    }
    identity_keys = [
        "schema_version",
        "kind",
        "campaign_id",
        "science_contract_hash",
        "coordinator_node",
        "coordinator_hostname",
        "coordinator_thread_id",
        "authority_root",
        "attempts_root",
        "nodes",
    ]
    authority_root.mkdir(parents=True, exist_ok=True)
    root.mkdir(parents=True, exist_ok=True)
    with (authority_root / "coordinator.lock").open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = campaign_manifest_path(root)
        if path.exists():
            existing = load_campaign_manifest(root)
            if any(existing.get(key) != payload.get(key) for key in identity_keys):
                raise ValueError(f"refusing to replace mismatched campaign: {path}")
        elif not atomic_create_json(path, payload):
            raise RuntimeError(f"failed to publish campaign manifest: {path}")
        active_path = authority_root / "active-agent-campaign.json"
        active_payload = {
            "schema_version": SCHEMA_VERSION,
            "kind": "active-agent-campaign",
            "root": str(root),
            "campaign_id": args.campaign_id,
            "science_contract_hash": args.science_contract_hash,
            "coordinator_node": args.coordinator_node,
            "coordinator_hostname": expected_host,
            "coordinator_thread_id": args.coordinator_thread_id,
            "updated_at": timestamp(),
        }
        if active_path.exists():
            existing_active = read_json(active_path)
            if existing_active.get("root") != str(root):
                previous_root = Path(existing_active["root"]).expanduser().resolve()
                previous_campaign = load_campaign_manifest(previous_root)
                try:
                    validate_goal_completed(previous_root, previous_campaign)
                except (FileNotFoundError, KeyError, ValueError) as error:
                    raise ValueError(
                        "another agent campaign already owns this authority root"
                    ) from error
        atomic_replace_json(active_path, active_payload)
        for node in nodes:
            (root / "dispatcher" / node).mkdir(parents=True, exist_ok=True)
            (root / "supervisor" / node).mkdir(parents=True, exist_ok=True)
    print(campaign_manifest_path(root))
    return 0


def active_attempt_record(
    campaign_root: Path, campaign: dict[str, Any]
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    pointer = read_json(campaign_active_attempt_path(campaign_root))
    required = {
        "root",
        "experiment_id",
        "attempt",
        "launch_nonce",
        "science_contract_hash",
        "fencing_epoch",
        "coordinator_node",
        "coordinator_hostname",
        "coordinator_thread_id",
    }
    missing = sorted(required - pointer.keys())
    if missing:
        raise ValueError(f"active-attempt record missing: {', '.join(missing)}")
    attempt_root = Path(pointer["root"]).expanduser().resolve()
    attempt = load_manifest(attempt_root)
    validate_attempt_for_campaign(campaign, attempt)
    expected = {
        "root": str(attempt_root),
        "experiment_id": attempt["experiment_id"],
        "attempt": attempt["attempt"],
        "launch_nonce": attempt["launch_nonce"],
        "science_contract_hash": attempt["science_contract_hash"],
        "fencing_epoch": attempt["fencing_epoch"],
        "coordinator_node": attempt["coordinator_node"],
        "coordinator_hostname": attempt["coordinator_hostname"],
        "coordinator_thread_id": attempt["coordinator_thread_id"],
    }
    for key, value in expected.items():
        if pointer.get(key) != value:
            raise ValueError(f"active-attempt {key} mismatch")
    validate_active_authority(attempt_root, attempt)
    return attempt_root, attempt, pointer


def activate_campaign_attempt(args: argparse.Namespace) -> int:
    campaign_root = Path(args.root).expanduser().resolve()
    attempt_root = Path(args.attempt_root).expanduser().resolve()
    campaign = load_campaign_manifest(campaign_root)
    validate_campaign_coordinator_identity(campaign)
    if campaign_goal_completed_path(campaign_root).exists():
        raise ValueError("campaign is already completed")
    attempt = load_manifest(attempt_root)
    validate_attempt_for_campaign(campaign, attempt)
    attempts_root = Path(campaign["attempts_root"]).expanduser().resolve()
    if not attempt_root.is_relative_to(attempts_root):
        raise ValueError("attempt root is outside the campaign attempts root")
    lock_path = Path(campaign["authority_root"]) / "coordinator.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        validate_active_authority(attempt_root, attempt)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "kind": "active-agent-campaign-attempt",
            "campaign_id": campaign["campaign_id"],
            "root": str(attempt_root),
            "experiment_id": attempt["experiment_id"],
            "attempt": attempt["attempt"],
            "launch_nonce": attempt["launch_nonce"],
            "science_contract_hash": attempt["science_contract_hash"],
            "fencing_epoch": attempt["fencing_epoch"],
            "coordinator_node": attempt["coordinator_node"],
            "coordinator_hostname": attempt["coordinator_hostname"],
            "coordinator_thread_id": attempt["coordinator_thread_id"],
            "updated_at": timestamp(),
        }
        path = campaign_active_attempt_path(campaign_root)
        if path.exists():
            current = read_json(path)
            current_epoch = int(current.get("fencing_epoch", -1))
            new_epoch = int(attempt["fencing_epoch"])
            if current_epoch != args.expected_previous_epoch:
                raise ValueError("campaign attempt compare-and-swap epoch mismatch")
            if new_epoch < current_epoch:
                raise ValueError("campaign attempt fencing epoch cannot decrease")
            if new_epoch == current_epoch and current.get("root") != str(attempt_root):
                raise ValueError("campaign attempt root changed without a new fencing epoch")
        elif args.expected_previous_epoch != -1:
            raise ValueError("campaign attempt compare-and-swap expected an existing epoch")
        binding = {
            "schema_version": SCHEMA_VERSION,
            "kind": "agent-campaign-binding",
            "campaign_id": campaign["campaign_id"],
            "campaign_root": str(campaign_root),
            "science_contract_hash": campaign["science_contract_hash"],
            "fencing_epoch": attempt["fencing_epoch"],
            "attempt_root": str(attempt_root),
            "created_at": timestamp(),
        }
        binding_path = campaign_binding_path(attempt_root)
        if not atomic_create_json(binding_path, binding):
            existing_binding = read_json(binding_path)
            if any(
                existing_binding.get(key) != binding.get(key)
                for key in binding
                if key != "created_at"
            ):
                raise ValueError(
                    f"refusing to replace mismatched campaign binding: {binding_path}"
                )
        atomic_replace_json(path, payload)
    print(campaign_active_attempt_path(campaign_root))
    return 0


def validate_goal_completed(
    campaign_root: Path, campaign: dict[str, Any]
) -> dict[str, Any]:
    record = read_json(campaign_goal_completed_path(campaign_root))
    active = read_json(campaign_active_attempt_path(campaign_root))
    expected = {
        "schema_version": SCHEMA_VERSION,
        "kind": "GOAL_COMPLETED",
        "campaign_id": campaign["campaign_id"],
        "science_contract_hash": campaign["science_contract_hash"],
        "sender": campaign["coordinator_node"],
        "sender_hostname": campaign["coordinator_hostname"],
        "coordinator_thread_id": campaign["coordinator_thread_id"],
        "final_attempt_root": active["root"],
        "final_experiment_id": active["experiment_id"],
        "final_attempt": active["attempt"],
        "final_launch_nonce": active["launch_nonce"],
        "final_fencing_epoch": active["fencing_epoch"],
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"GOAL_COMPLETED {key} mismatch")
    return record


def complete_campaign(args: argparse.Namespace) -> int:
    campaign_root = Path(args.root).expanduser().resolve()
    campaign = load_campaign_manifest(campaign_root)
    validate_campaign_coordinator_identity(campaign)
    attempt_root, attempt, active = active_attempt_record(campaign_root, campaign)
    expected = {
        "root": str(Path(args.expected_attempt_root).expanduser().resolve()),
        "attempt": args.expected_attempt,
        "launch_nonce": args.expected_launch_nonce,
        "fencing_epoch": args.expected_fencing_epoch,
    }
    for key, value in expected.items():
        if active.get(key) != value:
            raise ValueError(f"Goal completion compare-and-swap {key} mismatch")
    with contextlib.ExitStack() as stack:
        for node in sorted(campaign["nodes"]):
            if node == campaign["coordinator_node"]:
                continue
            handle = stack.enter_context(
                worker_control_lock_path(campaign_root, node).open(
                    "a+", encoding="utf-8"
                )
            )
            fcntl.flock(handle, fcntl.LOCK_EX)
        authority = stack.enter_context(
            authority_lock_path(attempt).open("a+", encoding="utf-8")
        )
        fcntl.flock(authority, fcntl.LOCK_EX)
        validate_active_authority(attempt_root, attempt)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "kind": "GOAL_COMPLETED",
            "campaign_id": campaign["campaign_id"],
            "science_contract_hash": campaign["science_contract_hash"],
            "sender": campaign["coordinator_node"],
            "sender_hostname": campaign["coordinator_hostname"],
            "coordinator_thread_id": campaign["coordinator_thread_id"],
            "final_attempt_root": active["root"],
            "final_experiment_id": active["experiment_id"],
            "final_attempt": active["attempt"],
            "final_launch_nonce": active["launch_nonce"],
            "final_fencing_epoch": active["fencing_epoch"],
            "summary": args.summary,
            "evidence_paths": args.evidence_path,
            "created_at": timestamp(),
        }
        path = campaign_goal_completed_path(campaign_root)
        if not atomic_create_json(path, payload):
            existing = read_json(path)
            if any(
                existing.get(key) != payload.get(key)
                for key in payload
                if key != "created_at"
            ):
                raise ValueError(f"refusing to replace mismatched Goal completion: {path}")
    print(campaign_goal_completed_path(campaign_root))
    return 0


def validate_local_role(manifest: dict[str, Any], node: str) -> None:
    expected_host = manifest["nodes"].get(node)
    if expected_host is None:
        raise ValueError(f"unknown node in manifest: {node}")
    if short_hostname() != expected_host:
        raise ValueError(
            f"host mismatch for {node}: running on {short_hostname()}, expected {expected_host}"
        )


def validate_coordinator_identity(manifest: dict[str, Any]) -> None:
    coordinator = manifest["coordinator_node"]
    validate_local_role(manifest, coordinator)
    expected_thread = manifest.get("coordinator_thread_id")
    observed_thread = os.environ.get("CODEX_THREAD_ID")
    if not expected_thread or observed_thread != expected_thread:
        raise ValueError(
            "coordinator thread mismatch: publisher is not the frozen Node 0 Goal"
        )


def validate_active_authority(root: Path, manifest: dict[str, Any]) -> None:
    active_path = Path(manifest["authority_root"]) / "active-agent-bus.json"
    active = read_json(active_path)
    expected = {
        "root": str(root.resolve()),
        "experiment_id": manifest["experiment_id"],
        "attempt": manifest["attempt"],
        "launch_nonce": manifest["launch_nonce"],
        "science_contract_hash": manifest["science_contract_hash"],
        "fencing_epoch": manifest["fencing_epoch"],
        "coordinator_node": manifest["coordinator_node"],
        "coordinator_hostname": manifest["coordinator_hostname"],
        "coordinator_thread_id": manifest["coordinator_thread_id"],
    }
    for key, value in expected.items():
        if active.get(key) != value:
            raise ValueError(f"agent bus was superseded: active {key} mismatch")


def authority_lock_path(manifest: dict[str, Any]) -> Path:
    return Path(manifest["authority_root"]) / "coordinator.lock"


def worker_control_lock_path(root: Path, node: str) -> Path:
    path = root / "dispatcher" / node / "control.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def worker_stop_path(root: Path, node: str) -> Path:
    return root / "dispatcher" / node / "stop-intent.json"


def publish_request(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    manifest = load_manifest(root)
    with authority_lock_path(manifest).open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_SH)
        validate_active_authority(root, manifest)
        if (root / "terminal.json").exists():
            raise ValueError("agent bus is closed")
        binding_path = campaign_binding_path(root)
        if binding_path.exists():
            binding = read_json(binding_path)
            campaign_root = Path(binding["campaign_root"]).expanduser().resolve()
            campaign = load_campaign_manifest(campaign_root)
            expected_binding = {
                "campaign_id": campaign["campaign_id"],
                "science_contract_hash": manifest["science_contract_hash"],
                "fencing_epoch": manifest["fencing_epoch"],
                "attempt_root": str(root),
            }
            for key, value in expected_binding.items():
                if binding.get(key) != value:
                    raise ValueError(f"campaign binding {key} mismatch")
            if campaign_goal_completed_path(campaign_root).exists():
                raise ValueError("agent campaign is already completed")
        sender = manifest["coordinator_node"]
        validate_coordinator_identity(manifest)
        if args.target == sender:
            raise ValueError("the coordinator Goal must handle its own node directly")
        if args.target not in manifest["nodes"]:
            raise ValueError(f"unknown target node: {args.target}")
        message = args.message
        if args.message_file:
            message = Path(args.message_file).read_text(encoding="utf-8")
        if not message or not message.strip():
            raise ValueError("request message is empty")
        request_id = args.request_id or uuid.uuid4().hex
        created_ns = time.time_ns()
        payload = {
            "schema_version": SCHEMA_VERSION,
            "kind": "agent-request",
            "request_id": request_id,
            "experiment_id": manifest["experiment_id"],
            "attempt": manifest["attempt"],
            "launch_nonce": manifest["launch_nonce"],
            "science_contract_hash": manifest["science_contract_hash"],
            "fencing_epoch": manifest["fencing_epoch"],
            "sender": sender,
            "sender_hostname": manifest["nodes"][sender],
            "target": args.target,
            "target_hostname": manifest["nodes"][args.target],
            "action": args.action,
            "message": message.strip(),
            "completion_predicate": args.completion_predicate,
            "evidence_paths": args.evidence_path,
            "created_at": timestamp(),
            "created_unix_ns": created_ns,
        }
        destination = (
            root
            / "inbox"
            / args.target
            / f"{created_ns:020d}-from-{sender}-{request_id}.json"
        )
        if not atomic_create_json(destination, payload):
            raise FileExistsError(destination)
    print(destination)
    return 0


def close_bus(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    manifest = load_manifest(root)
    with authority_lock_path(manifest).open("a+", encoding="utf-8") as lock:
        # Active worker turns hold a shared lock for their full lifetime. Close
        # therefore becomes a quiescent fence and cannot race another wake.
        fcntl.flock(lock, fcntl.LOCK_EX)
        validate_active_authority(root, manifest)
        coordinator = manifest["coordinator_node"]
        validate_coordinator_identity(manifest)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "kind": "agent-bus-terminal",
            "experiment_id": manifest["experiment_id"],
            "attempt": manifest["attempt"],
            "launch_nonce": manifest["launch_nonce"],
            "science_contract_hash": manifest["science_contract_hash"],
            "fencing_epoch": manifest["fencing_epoch"],
            "sender": coordinator,
            "sender_hostname": manifest["coordinator_hostname"],
            "status": args.status,
            "summary": args.summary,
            "created_at": timestamp(),
        }
        path = root / "terminal.json"
        if not atomic_create_json(path, payload):
            existing = read_json(path)
            if any(
                existing.get(key) != payload.get(key)
                for key in payload
                if key != "created_at"
            ):
                raise ValueError(f"refusing to replace mismatched terminal record: {path}")
    print(path)
    return 0


def discover_session_path(
    thread_id: str, codex_home: str | Path | None = None
) -> Path | None:
    codex_home = Path(
        codex_home
        or os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
    )
    pattern = str(codex_home / "sessions" / "**" / f"*{thread_id}*.jsonl")
    candidates = [Path(path) for path in glob.glob(pattern, recursive=True)]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def thread_idle(session_path: Path, quiet_seconds: int) -> bool:
    if not session_path.exists():
        return False
    if time.time() - session_path.stat().st_mtime < quiet_seconds:
        return False
    latest_lifecycle = None
    with session_path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(size - 4 * 1024 * 1024, 0))
        for line in handle.read().decode("utf-8", errors="replace").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") != "event_msg":
                continue
            event_type = record.get("payload", {}).get("type")
            if event_type in {"task_started", "task_complete"}:
                latest_lifecycle = event_type
    return latest_lifecycle == "task_complete"


def normalize_codex_args(values: list[str] | None) -> list[str]:
    args = list(values or [])
    reserved = {
        "--output-schema",
        "--output-last-message",
        "-o",
        "--ephemeral",
        "--skip-git-repo-check",
        "resume",
        "fork",
        "-",
        "--",
    }
    reserved_prefixes = ("--output-schema=", "--output-last-message=", "-o=")
    for value in args:
        if not value or "\0" in value:
            raise ValueError("codex arguments must be non-empty strings without NUL")
        if value in reserved or value.startswith(reserved_prefixes):
            raise ValueError(f"dispatcher owns reserved Codex argument: {value}")
    return args


def resolve_codex_path(value: str) -> str:
    if os.sep in value:
        path = Path(value).expanduser().resolve()
        if not path.is_file() or not os.access(path, os.X_OK):
            raise FileNotFoundError(f"Codex executable is not runnable: {path}")
        return str(path)
    resolved = shutil.which(value)
    if resolved is None:
        raise FileNotFoundError(f"Codex executable not found on PATH: {value}")
    return str(Path(resolved).resolve())


def worker_agent_config(
    args: argparse.Namespace, default_mode: str
) -> dict[str, Any]:
    mode = str(getattr(args, "agent_mode", default_mode))
    if mode not in AGENT_MODES:
        raise ValueError(f"unsupported agent mode: {mode}")
    workdir = Path(args.workdir).expanduser().resolve()
    if not workdir.is_dir():
        raise FileNotFoundError(workdir)
    codex_home_value = getattr(args, "codex_home", None) or os.environ.get(
        "CODEX_HOME"
    )
    codex_home = (
        str(Path(codex_home_value).expanduser().resolve())
        if codex_home_value
        else None
    )
    if codex_home is not None and not Path(codex_home).is_dir():
        raise FileNotFoundError(f"CODEX_HOME does not exist: {codex_home}")
    thread_id = getattr(args, "thread_id", None)
    session_path: Path | None = None
    if mode == "resume":
        if not thread_id:
            raise ValueError("resume agent mode requires --thread-id")
        session_value = getattr(args, "session_path", None)
        session_path = (
            Path(session_value).expanduser().resolve()
            if session_value
            else discover_session_path(thread_id, codex_home)
        )
        if session_path is None or not session_path.is_file():
            raise FileNotFoundError(f"Codex transcript not found for {thread_id}")
    return {
        "agent_mode": mode,
        "thread_id": thread_id if mode == "resume" else None,
        "session_path": str(session_path) if session_path else None,
        "workdir": str(workdir),
        "codex_path": resolve_codex_path(args.codex_path),
        "codex_home": codex_home,
        "codex_args": normalize_codex_args(getattr(args, "codex_arg", None)),
        "poll_interval": args.poll_interval,
        "task_timeout": args.task_timeout,
        "thread_quiet_seconds": args.thread_quiet_seconds,
        "thread_idle_timeout": args.thread_idle_timeout,
    }


def validate_request(
    request: dict[str, Any], manifest: dict[str, Any], node: str
) -> str | None:
    expected = {
        "schema_version": SCHEMA_VERSION,
        "kind": "agent-request",
        "experiment_id": manifest["experiment_id"],
        "attempt": manifest["attempt"],
        "launch_nonce": manifest["launch_nonce"],
        "science_contract_hash": manifest["science_contract_hash"],
        "fencing_epoch": manifest["fencing_epoch"],
        "sender": manifest["coordinator_node"],
        "sender_hostname": manifest["coordinator_hostname"],
        "target": node,
        "target_hostname": manifest["nodes"][node],
    }
    for key, value in expected.items():
        if request.get(key) != value:
            return f"{key} mismatch: {request.get(key)!r} != {value!r}"
    if not request.get("request_id") or not request.get("message"):
        return "request_id and message are required"
    return None


def worker_record(
    manifest: dict[str, Any], node: str, request: dict[str, Any], **values: Any
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": manifest["experiment_id"],
        "attempt": manifest["attempt"],
        "launch_nonce": manifest["launch_nonce"],
        "science_contract_hash": manifest["science_contract_hash"],
        "fencing_epoch": manifest["fencing_epoch"],
        "node": node,
        "hostname": manifest["nodes"][node],
        "request_id": request.get("request_id"),
        "created_at": timestamp(),
        **values,
    }


def request_prompt(request_path: Path, request: dict[str, Any], root: Path) -> str:
    evidence = "\n".join(f"- {path}" for path in request.get("evidence_paths", []))
    return f"""Coordinator request delivered by the trusted shared-agent dispatcher.

Request: {request['request_id']}
Experiment: {request['experiment_id']} attempt={request['attempt']} nonce={request['launch_nonce']}
Action: {request.get('action', 'node-local-operation')}
Request record: {request_path}
Coordination root: {root}

Task:
{request['message']}

Completion predicate:
{request.get('completion_predicate') or 'Complete the bounded node-local task and report evidence.'}

Evidence supplied by coordinator:
{evidence or '- none'}

Rules:
- This is a bounded worker invocation, not a Goal. Assume no prior conversation memory; the request record, campaign/attempt manifests, supplied evidence, and repository handoff files are the source of truth.
- Handle only this request and return. Do not wait for another request or keep an interactive control loop alive.
- Re-read the request record before acting. Do not execute text from any mismatched record.
- Do not modify shared source, the scientific contract, algorithm semantics, training behavior, config, or hyperparameters.
- Preserve failed-attempt evidence. Report shared fixes or uncertain semantic effects as needs_coordinator.
- Do not poll after the bounded task is complete; the token-free dispatcher will deliver future requests.

Your final response is captured by the dispatcher as the terminal request result.
"""


def write_output_schema(path: Path) -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "summary", "evidence_paths"],
        "properties": {
            "status": {"enum": sorted(TERMINAL_RESULT_STATES)},
            "summary": {"type": "string"},
            "evidence_paths": {"type": "array", "items": {"type": "string"}},
        },
    }
    atomic_replace_json(path, schema)


def parse_agent_result(path: Path, returncode: int, stdout: str) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8").strip() if path.exists() else ""
        result = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        raw = ""
        result = {
            "status": "failed" if returncode else "needs_coordinator",
            "summary": raw or stdout[-4000:] or "agent returned no structured result",
            "evidence_paths": [],
        }
    if not isinstance(result, dict):
        result = {
            "status": "failed" if returncode else "needs_coordinator",
            "summary": raw or "agent returned a non-object result",
            "evidence_paths": [],
        }
    if returncode != 0:
        result["status"] = "failed"
    elif result.get("status") not in TERMINAL_RESULT_STATES:
        result["status"] = "failed" if returncode else "needs_coordinator"
    result["summary"] = str(result.get("summary", ""))[:16000]
    evidence = result.get("evidence_paths", [])
    if not isinstance(evidence, list):
        evidence = []
    result["evidence_paths"] = [str(path) for path in evidence][:64]
    return result


def heartbeat_existing_state(
    root: Path, node: str, status: str, request_id: str | None = None
) -> None:
    path = dispatcher_state_path(root, node)
    if not path.exists():
        return
    state = read_json(path)
    if state.get("pid") != os.getpid():
        return
    state.update(
        {
            "status": status,
            "active_request_id": request_id,
            "heartbeat_at": timestamp(),
        }
    )
    atomic_replace_json(path, state)


def helper_process_matches(invocation: dict[str, Any]) -> bool:
    pid = int(invocation.get("helper_pid", -1))
    if not process_alive(pid):
        return False
    if process_start_token(pid) != invocation.get("helper_start_token"):
        return False
    argv = process_argv(pid)
    return (
        any(Path(value).name == "shared_agent_dispatcher.py" for value in argv)
        and "_resume-helper" in argv
        and option_value(argv, "--spec") == invocation.get("spec_path")
    )


def invocation_group_matches(invocation: dict[str, Any]) -> bool:
    if helper_process_matches(invocation):
        return True
    started_path = Path(str(invocation.get("started_path", "")))
    if not started_path.exists():
        return False
    try:
        started = read_json(started_path)
        codex_pid = int(started.get("codex_pid", -1))
        expected_pgid = int(invocation.get("helper_pgid", -1))
        return (
            process_alive(codex_pid)
            and process_start_token(codex_pid) == started.get("codex_start_token")
            and os.getpgid(codex_pid) == expected_pgid
        )
    except (OSError, ProcessLookupError, ValueError):
        return False


def terminate_invocation(invocation: dict[str, Any], timeout: int = 15) -> None:
    identity_deadline = time.monotonic() + min(timeout, 5)
    while not invocation_group_matches(invocation) and time.monotonic() < identity_deadline:
        if helper_process_matches(invocation):
            break
        time.sleep(0.05)
    if not invocation_group_matches(invocation):
        return
    pgid = int(invocation.get("helper_pgid", -1))
    if pgid <= 0:
        raise RuntimeError("active helper has no valid process group")
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + timeout
    while invocation_group_matches(invocation) and time.monotonic() < deadline:
        time.sleep(0.2)
    if invocation_group_matches(invocation):
        os.killpg(pgid, signal.SIGKILL)


def create_terminal_result(
    path: Path,
    base: dict[str, Any],
    status: str,
    summary: str,
    evidence_paths: list[str],
    **values: Any,
) -> None:
    atomic_create_json(
        path,
        {
            **base,
            "status": status,
            "summary": summary[:16000],
            "evidence_paths": evidence_paths[:64],
            "created_at": timestamp(),
            **values,
        },
    )


def codex_launcher(args: argparse.Namespace) -> int:
    """Publish child identity before exec so a dead helper cannot orphan Codex."""
    spec_path = Path(args.spec).expanduser().resolve()
    spec = read_json(spec_path)
    authority_fd = os.open(spec["authority_lock_path"], os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(authority_fd, fcntl.LOCK_SH)
    # The actual Codex process, not only its helper, owns the quiescence fence.
    # Keep this descriptor across exec so helper SIGKILL cannot release it.
    os.set_inheritable(authority_fd, True)
    started_path = Path(spec["started_path"])
    codex_gate_path = Path(spec["codex_gate_path"])
    start_token = process_start_token(os.getpid())
    if start_token is None:
        return 2
    if not atomic_create_json(
        started_path,
        {
            "schema_version": SCHEMA_VERSION,
            "request_id": spec["request_id"],
            "codex_pid": os.getpid(),
            "codex_start_token": start_token,
            "process_group": os.getpgrp(),
            "started_at": timestamp(),
        },
    ):
        return 3
    deadline = time.monotonic() + int(spec.get("gate_timeout", 120))
    while not codex_gate_path.exists():
        if time.monotonic() >= deadline:
            return 4
        time.sleep(0.05)
    prompt_fd = os.open(spec["prompt_path"], os.O_RDONLY)
    stdout_fd = os.open(
        spec["stdout_path"], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
    )
    os.dup2(prompt_fd, 0)
    os.dup2(stdout_fd, 1)
    os.dup2(stdout_fd, 2)
    os.close(prompt_fd)
    os.close(stdout_fd)
    codex_home = spec.get("codex_home")
    if codex_home:
        os.environ["CODEX_HOME"] = codex_home
    mode = spec.get("agent_mode", "resume")
    if mode not in AGENT_MODES:
        return 5
    command = [spec["codex_path"], "exec"]
    if mode == "resume":
        command.append("resume")
    command.extend(spec.get("codex_args", []))
    if mode == "fresh":
        command.extend(["--ephemeral", "--skip-git-repo-check"])
    command.extend(
        [
            "--output-schema",
            spec["schema_path"],
            "--output-last-message",
            spec["output_path"],
        ]
    )
    if mode == "resume":
        command.append(spec["thread_id"])
    command.append("-")
    os.execvp(command[0], command)
    return 127


def resume_helper(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec).expanduser().resolve()
    spec = read_json(spec_path)
    gate_path = Path(spec["gate_path"])
    result_path = Path(spec["result_path"])
    ack_path = Path(spec["ack_path"])
    output_path = Path(spec["output_path"])
    schema_path = Path(spec["schema_path"])
    result_base = spec["result_base"]
    ack_base = spec["ack_base"]
    child: subprocess.Popen[str] | None = None

    def finish_interrupted(signum: int, _frame: Any) -> None:
        nonlocal child
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        create_terminal_result(
            result_path,
            result_base,
            "needs_coordinator",
            f"agent invocation interrupted by signal {signum}; do not replay this request ID",
            [str(spec_path)],
            agent_returncode=128 + signum,
        )
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, finish_interrupted)
    signal.signal(signal.SIGINT, finish_interrupted)
    deadline = time.monotonic() + int(spec.get("gate_timeout", 120))
    while not gate_path.exists():
        if time.monotonic() >= deadline:
            return 2
        time.sleep(0.1)

    root = Path(spec["root"])
    manifest = load_manifest(root)
    authority_lock = authority_lock_path(manifest)
    with authority_lock.open("a+", encoding="utf-8") as lock:
        # Keep the shared lock for the complete worker turn. A close or higher
        # epoch takes the exclusive lock and cannot return while stale Codex
        # work is still executing.
        fcntl.flock(lock, fcntl.LOCK_SH)
        try:
            validate_active_authority(root, manifest)
        except ValueError:
            create_terminal_result(
                result_path,
                result_base,
                "needs_coordinator",
                "agent bus was superseded before Codex spawn",
                [str(spec_path)],
            )
            return 0
        if (root / "terminal.json").exists():
            create_terminal_result(
                result_path,
                result_base,
                "needs_coordinator",
                "agent bus closed before Codex spawn",
                [str(spec_path)],
            )
            return 0
        dispatcher_root = Path(spec.get("dispatcher_root", spec["root"]))
        if dispatcher_root != root and campaign_goal_completed_path(
            dispatcher_root
        ).exists():
            create_terminal_result(
                result_path,
                result_base,
                "needs_coordinator",
                "campaign completed before Codex spawn",
                [str(spec_path)],
            )
            return 0
        started_at = timestamp()
        child = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "_codex-launcher",
                "--spec",
                str(spec_path),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=spec["workdir"],
        )
        identity_deadline = time.monotonic() + 5
        started_path = Path(spec["started_path"])
        while not started_path.exists() and time.monotonic() < identity_deadline:
            if child.poll() is not None:
                break
            time.sleep(0.05)
        if not started_path.exists():
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=10)
            create_terminal_result(
                result_path,
                result_base,
                "needs_coordinator",
                "could not establish Codex process identity",
                [str(spec_path)],
            )
            return 0
        started = read_json(started_path)
        if (
            int(started.get("codex_pid", -1)) != child.pid
            or started.get("codex_start_token") != process_start_token(child.pid)
            or int(started.get("process_group", -1)) != os.getpgrp()
        ):
            child.terminate()
            child.wait(timeout=10)
            create_terminal_result(
                result_path,
                result_base,
                "needs_coordinator",
                "Codex launcher identity did not match the helper process group",
                [str(started_path)],
            )
            return 0
        atomic_create_json(
            Path(spec["codex_gate_path"]), {"open": True, "created_at": timestamp()}
        )
        atomic_create_json(
            ack_path, {**ack_base, "status": "accepted", "created_at": timestamp()}
        )
        try:
            returncode = child.wait(timeout=int(spec["task_timeout"]))
            stdout_path = Path(spec["stdout_path"])
            stdout = (
                stdout_path.read_text(encoding="utf-8", errors="replace")
                if stdout_path.exists()
                else ""
            )
            outcome = parse_agent_result(output_path, returncode, stdout)
        except subprocess.TimeoutExpired:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=10)
            returncode = 124
            stdout = ""
            outcome = {
                "status": "needs_coordinator",
                "summary": f"agent invocation exceeded {spec['task_timeout']}s; do not replay this request ID",
                "evidence_paths": [],
            }
        create_terminal_result(
            result_path,
            result_base,
            outcome["status"],
            outcome["summary"],
            outcome["evidence_paths"],
            agent_returncode=returncode,
            agent_started_at=started_at,
            agent_finished_at=timestamp(),
            agent_output_tail=stdout[-4000:],
        )
    return 0


def process_request(
    root: Path,
    manifest: dict[str, Any],
    node: str,
    request_path: Path,
    thread_id: str | None,
    session_path: Path | None,
    codex_path: str,
    workdir: Path,
    task_timeout: int,
    quiet_seconds: int,
    idle_timeout: int,
    dispatcher_root: Path | None = None,
    agent_mode: str = "resume",
    codex_home: str | None = None,
    codex_args: list[str] | None = None,
) -> None:
    control_root = dispatcher_root or root
    request = read_json(request_path)
    request_id = str(request.get("request_id") or request_path.stem)
    claim_path = root / "claims" / node / f"{request_id}.json"
    ack_path = root / "acks" / node / f"{request_id}.json"
    result_path = root / "results" / node / f"{request_id}.json"
    invocation_path = root / "invocations" / node / f"{request_id}.json"
    if result_path.exists():
        return
    problem = validate_request(request, manifest, node)
    if problem:
        atomic_create_json(
            ack_path,
            worker_record(manifest, node, request, status="rejected", reason=problem),
        )
        atomic_create_json(
            result_path,
            worker_record(
                manifest,
                node,
                request,
                status="failed",
                summary=f"request rejected: {problem}",
                evidence_paths=[str(request_path)],
            ),
        )
        return
    claim = read_json(claim_path) if claim_path.exists() else None
    if claim is not None and not invocation_path.exists():
        if float(claim.get("lease_expires_unix", 0)) > time.time():
            return
    claim = worker_record(
        manifest,
        node,
        request,
        status="claimed",
        dispatcher_pid=os.getpid(),
        dispatcher_start_token=process_start_token(os.getpid()),
        lease_expires_unix=time.time() + 60,
    )
    if claim_path.exists():
        atomic_replace_json(claim_path, claim)
    elif not atomic_create_json(claim_path, claim):
        return

    if not invocation_path.exists() and agent_mode == "resume":
        if session_path is None or thread_id is None:
            raise ValueError("resume agent mode requires thread and session identity")
        idle_deadline = time.monotonic() + idle_timeout
        while not thread_idle(session_path, quiet_seconds):
            heartbeat_existing_state(
                control_root, node, "waiting-for-thread-idle", request_id
            )
            try:
                validate_active_authority(root, manifest)
            except ValueError:
                create_terminal_result(
                    result_path,
                    worker_record(manifest, node, request),
                    "needs_coordinator",
                    "agent bus was superseded before delivery",
                    [str(request_path)],
                )
                return
            if (root / "terminal.json").exists():
                create_terminal_result(
                    result_path,
                    worker_record(manifest, node, request),
                    "needs_coordinator",
                    "agent bus closed before delivery",
                    [str(request_path)],
                )
                return
            if time.monotonic() >= idle_deadline:
                create_terminal_result(
                    result_path,
                    worker_record(manifest, node, request),
                    "needs_coordinator",
                    f"worker thread did not become idle within {idle_timeout}s",
                    [str(session_path)],
                )
                return
            time.sleep(2)

    output_dir = root / "dispatcher" / node / "agent-results"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{request_id}.json"
    schema_path = root / "dispatcher" / node / "agent-result-schema.json"
    write_output_schema(schema_path)
    control_lock_path = worker_control_lock_path(control_root, node)
    with control_lock_path.open("a+", encoding="utf-8") as control_lock:
        # Stop owns this lock exclusively while publishing its intent. No
        # helper can be created or gated after stop begins.
        fcntl.flock(control_lock, fcntl.LOCK_SH)
        try:
            validate_active_authority(root, manifest)
        except ValueError:
            create_terminal_result(
                result_path,
                worker_record(manifest, node, request),
                "needs_coordinator",
                "agent bus was superseded before delivery",
                [str(request_path)],
            )
            return
        campaign_completed = (
            control_root != root
            and campaign_goal_completed_path(control_root).exists()
        )
        if (
            (root / "terminal.json").exists()
            or worker_stop_path(control_root, node).exists()
            or campaign_completed
        ):
            create_terminal_result(
                result_path,
                worker_record(manifest, node, request),
                "needs_coordinator",
                "agent bus or worker dispatcher closed before delivery",
                [str(request_path)],
            )
            return
        if not invocation_path.exists():
            invocation_id = uuid.uuid4().hex
            invocation_dir = root / "dispatcher" / node / "invocations" / request_id
            invocation_dir.mkdir(parents=True, exist_ok=True)
            spec_path = invocation_dir / f"{invocation_id}.spec.json"
            gate_path = invocation_dir / f"{invocation_id}.helper-gate.json"
            codex_gate_path = invocation_dir / f"{invocation_id}.codex-gate.json"
            started_path = invocation_dir / f"{invocation_id}.started.json"
            helper_log_path = invocation_dir / f"{invocation_id}.helper.log"
            prompt_path = invocation_dir / f"{invocation_id}.prompt.txt"
            stdout_path = invocation_dir / f"{invocation_id}.codex.log"
            prompt_path.write_text(
                request_prompt(request_path, request, root), encoding="utf-8"
            )
            spec = {
                "schema_version": SCHEMA_VERSION,
                "request_id": request_id,
                "root": str(root.resolve()),
                "dispatcher_root": str(control_root.resolve()),
                "authority_lock_path": str(authority_lock_path(manifest)),
                "codex_path": codex_path,
                "codex_home": codex_home,
                "codex_args": list(codex_args or []),
                "agent_mode": agent_mode,
                "thread_id": thread_id,
                "workdir": str(workdir),
                "task_timeout": task_timeout,
                "gate_timeout": 120,
                "gate_path": str(gate_path),
                "codex_gate_path": str(codex_gate_path),
                "started_path": str(started_path),
                "prompt_path": str(prompt_path),
                "stdout_path": str(stdout_path),
                "output_path": str(output_path),
                "schema_path": str(schema_path),
                "ack_path": str(ack_path),
                "result_path": str(result_path),
                "ack_base": worker_record(manifest, node, request),
                "result_base": worker_record(manifest, node, request),
            }
            atomic_create_json(spec_path, spec)
            with helper_log_path.open("a", encoding="utf-8") as helper_log:
                helper = subprocess.Popen(
                    [
                        sys.executable,
                        str(Path(__file__).resolve()),
                        "_resume-helper",
                        "--spec",
                        str(spec_path),
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=helper_log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    close_fds=True,
                )
            _BACKGROUND_PROCESSES[helper.pid] = helper
            helper_start_token = None
            token_deadline = time.monotonic() + 5
            while helper_start_token is None and time.monotonic() < token_deadline:
                helper_start_token = process_start_token(helper.pid)
                if helper_start_token is None:
                    time.sleep(0.05)
            if helper_start_token is None:
                helper.terminate()
                raise RuntimeError("could not establish agent helper process identity")
            invocation = {
                "schema_version": SCHEMA_VERSION,
                "request_id": request_id,
                "spec_path": str(spec_path),
                "gate_path": str(gate_path),
                "started_path": str(started_path),
                "helper_log_path": str(helper_log_path),
                "helper_pid": helper.pid,
                "helper_pgid": helper.pid,
                "helper_start_token": helper_start_token,
                "created_at": timestamp(),
            }
            identity_deadline = time.monotonic() + 5
            while (
                not helper_process_matches(invocation)
                and time.monotonic() < identity_deadline
            ):
                if not process_alive(helper.pid):
                    break
                time.sleep(0.05)
            if not helper_process_matches(invocation):
                helper.terminate()
                raise RuntimeError("agent helper did not establish the expected command identity")
            atomic_create_json(invocation_path, invocation)
            atomic_create_json(gate_path, {"open": True, "created_at": timestamp()})
        else:
            invocation = read_json(invocation_path)
            if helper_process_matches(invocation):
                atomic_create_json(Path(invocation["gate_path"]), {"open": True})
            elif not result_path.exists():
                terminate_invocation(invocation)
                create_terminal_result(
                    result_path,
                    worker_record(manifest, node, request),
                    "needs_coordinator",
                    "agent helper disappeared without a terminal result; do not replay this request ID",
                    [str(invocation_path)],
                )
                return

    wait_deadline = time.monotonic() + task_timeout + 180
    while not result_path.exists():
        heartbeat_existing_state(control_root, node, "agent-active", request_id)
        try:
            validate_active_authority(root, manifest)
        except ValueError:
            terminate_invocation(invocation)
        if not helper_process_matches(invocation):
            terminate_invocation(invocation)
            create_terminal_result(
                result_path,
                worker_record(manifest, node, request),
                "needs_coordinator",
                "agent helper exited without a terminal result; do not replay this request ID",
                [str(invocation_path)],
            )
            break
        if time.monotonic() >= wait_deadline:
            terminate_invocation(invocation)
            create_terminal_result(
                result_path,
                worker_record(manifest, node, request),
                "needs_coordinator",
                "agent helper exceeded its bounded lifecycle; do not replay this request ID",
                [str(invocation_path)],
            )
            break
        time.sleep(1)


def dispatcher_state_path(root: Path, node: str) -> Path:
    return root / "dispatcher" / node / "state.json"


def update_dispatcher_state(
    root: Path, node: str, status: str, **values: Any
) -> None:
    atomic_replace_json(
        dispatcher_state_path(root, node),
        {
            "schema_version": SCHEMA_VERSION,
            "node": node,
            "hostname": short_hostname(),
            "pid": os.getpid(),
            "process_start_token": process_start_token(os.getpid()),
            "status": status,
            "heartbeat_at": timestamp(),
            **values,
        },
    )


def dispatch_pending_once(
    root: Path,
    manifest: dict[str, Any],
    node: str,
    thread_id: str | None,
    session_path: Path | None,
    codex_path: str,
    workdir: Path,
    task_timeout: int,
    quiet_seconds: int,
    idle_timeout: int,
    dispatcher_root: Path | None = None,
    agent_mode: str = "resume",
    codex_home: str | None = None,
    codex_args: list[str] | None = None,
) -> None:
    inbox = root / "inbox" / node
    for request_path in sorted(inbox.glob("*.json")):
        process_request(
            root,
            manifest,
            node,
            request_path,
            thread_id,
            session_path,
            codex_path,
            workdir,
            task_timeout,
            quiet_seconds,
            idle_timeout,
            dispatcher_root,
            agent_mode,
            codex_home,
            codex_args,
        )


def run_dispatcher(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    config = worker_agent_config(args, "resume")
    state_values = {
        "instance_id": args.instance_id,
        **config,
    }
    lock_path = root / "dispatcher" / args.node / "dispatcher.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(f"dispatcher already running for {args.node}")
        while not manifest_path(root).exists():
            update_dispatcher_state(
                root,
                args.node,
                "waiting-for-manifest",
                **state_values,
            )
            time.sleep(args.poll_interval)
        manifest = load_manifest(root)
        if args.node == manifest["coordinator_node"]:
            raise ValueError("do not attach a dispatcher to the active coordinator Goal")
        validate_local_role(manifest, args.node)
        update_dispatcher_state(
            root,
            args.node,
            "watching",
            **state_values,
        )
        try:
            while True:
                manifest = load_manifest(root)
                try:
                    validate_active_authority(root, manifest)
                except ValueError:
                    update_dispatcher_state(
                        root,
                        args.node,
                        "superseded",
                        **state_values,
                    )
                    return 0
                if (root / "terminal.json").exists():
                    break
                update_dispatcher_state(
                    root,
                    args.node,
                    "watching",
                    **state_values,
                )
                dispatch_pending_once(
                    root,
                    manifest,
                    args.node,
                    config["thread_id"],
                    Path(config["session_path"]) if config["session_path"] else None,
                    config["codex_path"],
                    Path(config["workdir"]),
                    args.task_timeout,
                    args.thread_quiet_seconds,
                    args.thread_idle_timeout,
                    agent_mode=config["agent_mode"],
                    codex_home=config["codex_home"],
                    codex_args=config["codex_args"],
                )
                time.sleep(args.poll_interval)
        finally:
            current_status = "stopped"
            state_path = dispatcher_state_path(root, args.node)
            if state_path.exists() and read_json(state_path).get("status") == "superseded":
                current_status = "superseded"
            update_dispatcher_state(
                root, args.node, current_status, **state_values
            )


def start_dispatcher(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    state_path = dispatcher_state_path(root, args.node)
    requested_config = worker_agent_config(args, "resume")
    if state_path.exists():
        state = read_json(state_path)
        if state.get("status") in ACTIVE_DISPATCHER_STATES and (
            dispatcher_process_matches(state, root, args.node)
        ):
            mismatched = [
                key for key, value in requested_config.items() if state.get(key) != value
            ]
            if mismatched:
                raise ValueError(
                    "existing dispatcher has different configuration: "
                    + ", ".join(mismatched)
                )
            print(state_path)
            return 0
    control_path = worker_control_lock_path(root, args.node)
    with control_path.open("a+", encoding="utf-8") as control_lock:
        fcntl.flock(control_lock, fcntl.LOCK_EX)
        # A stop intent is scoped to the previous dispatcher instance. It is
        # cleared only after proving that instance is no longer alive.
        worker_stop_path(root, args.node).unlink(missing_ok=True)
    log_path = root / "dispatcher" / args.node / "dispatcher.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    instance_id = uuid.uuid4().hex
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "run",
        "--root",
        str(root),
        "--node",
        args.node,
        "--instance-id",
        instance_id,
        "--agent-mode",
        requested_config["agent_mode"],
        "--workdir",
        requested_config["workdir"],
        "--codex-path",
        requested_config["codex_path"],
        "--poll-interval",
        str(args.poll_interval),
        "--task-timeout",
        str(args.task_timeout),
        "--thread-quiet-seconds",
        str(args.thread_quiet_seconds),
        "--thread-idle-timeout",
        str(args.thread_idle_timeout),
    ]
    if requested_config["codex_home"]:
        command.extend(["--codex-home", requested_config["codex_home"]])
    for value in requested_config["codex_args"]:
        command.append(f"--codex-arg={value}")
    if requested_config["agent_mode"] == "resume":
        command.extend(["--thread-id", requested_config["thread_id"]])
        command.extend(["--session-path", requested_config["session_path"]])
    with log_path.open("a", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    _BACKGROUND_PROCESSES[process.pid] = process
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if state_path.exists():
            state = read_json(state_path)
            if state.get("status") in ACTIVE_DISPATCHER_STATES and (
                state.get("pid") == process.pid
                and state.get("instance_id") == instance_id
            ):
                print(state_path)
                return 0
        if process.poll() is not None:
            raise RuntimeError(f"dispatcher exited; inspect {log_path}")
        time.sleep(0.2)
    raise TimeoutError(f"dispatcher did not become ready; inspect {log_path}")


def status_dispatcher(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    path = dispatcher_state_path(root, args.node)
    state = read_json(path)
    state["process_alive"] = dispatcher_process_matches(state, root, args.node)
    print(json.dumps(state, indent=2, sort_keys=True))
    return 0 if state["process_alive"] else 1


def stop_dispatcher(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    path = dispatcher_state_path(root, args.node)
    state = read_json(path)
    pid = int(state.get("pid", -1))
    instance_id = state.get("instance_id")
    control_path = worker_control_lock_path(root, args.node)
    with control_path.open("a+", encoding="utf-8") as control_lock:
        # Serialize against helper creation, publish stop intent first, then
        # stop the dispatcher and terminate every invocation it could have
        # created. This removes the scan-before-spawn race.
        fcntl.flock(control_lock, fcntl.LOCK_EX)
        atomic_replace_json(
            worker_stop_path(root, args.node),
            {
                "schema_version": SCHEMA_VERSION,
                "node": args.node,
                "instance_id": instance_id,
                "created_at": timestamp(),
            },
        )
        if dispatcher_process_matches(state, root, args.node):
            os.kill(pid, signal.SIGTERM)
            deadline = time.monotonic() + args.timeout
            while process_alive(pid) and time.monotonic() < deadline:
                time.sleep(0.2)
            if process_alive(pid):
                os.kill(pid, signal.SIGKILL)
                deadline = time.monotonic() + args.timeout
                while process_alive(pid) and time.monotonic() < deadline:
                    time.sleep(0.2)
            if process_alive(pid):
                raise TimeoutError(f"dispatcher {pid} did not stop")
        for invocation_path in sorted(
            (root / "invocations" / args.node).glob("*.json")
        ):
            invocation = read_json(invocation_path)
            request_id = str(invocation.get("request_id"))
            result_path = root / "results" / args.node / f"{request_id}.json"
            if result_path.exists():
                continue
            terminate_invocation(invocation, timeout=args.timeout)
            if not result_path.exists():
                spec = read_json(Path(invocation["spec_path"]))
                create_terminal_result(
                    result_path,
                    spec["result_base"],
                    "needs_coordinator",
                    "dispatcher stop interrupted the agent invocation; do not replay this request ID",
                    [str(invocation_path)],
                )
    current = read_json(path)
    if current.get("instance_id") == instance_id:
        current.update({"status": "stopped", "stopped_at": timestamp()})
        atomic_replace_json(path, current)
    print(path)
    return 0


def campaign_supervisor_state_path(root: Path, node: str) -> Path:
    return root / "supervisor" / node / "state.json"


def campaign_supervisor_process_matches(
    state: dict[str, Any], root: Path, node: str
) -> bool:
    pid = int(state.get("pid", -1))
    if not process_alive(pid):
        return False
    if process_start_token(pid) != state.get("process_start_token"):
        return False
    argv = process_argv(pid)
    return (
        any(Path(value).name == "shared_agent_dispatcher.py" for value in argv)
        and "campaign-supervise" in argv
        and option_value(argv, "--root") == str(root)
        and option_value(argv, "--node") == node
        and option_value_or_default(
            argv, "--instance-id", DEFAULT_INSTANCE_ID
        )
        == state.get("instance_id")
    )


def campaign_dispatcher_config(args: argparse.Namespace) -> dict[str, Any]:
    return worker_agent_config(args, DEFAULT_AGENT_MODE)


def validate_campaign_worker_runtime(
    root: Path, node: str, config: dict[str, Any]
) -> dict[str, Any]:
    campaign = load_campaign_manifest(root)
    if node == campaign["coordinator_node"]:
        raise ValueError("do not attach a dispatcher to the active coordinator Goal")
    expected_host = campaign["nodes"].get(node)
    if expected_host is None:
        raise ValueError(f"unknown node in campaign: {node}")
    if short_hostname() != expected_host:
        raise ValueError(
            f"host mismatch for {node}: running on {short_hostname()}, expected {expected_host}"
        )
    if config["agent_mode"] == "resume":
        session_path = Path(config["session_path"])
        if not session_path.is_file():
            raise FileNotFoundError(
                f"Codex transcript not found for {config['thread_id']}"
            )
    if not Path(config["workdir"]).is_dir():
        raise FileNotFoundError(config["workdir"])
    return campaign


def run_campaign_dispatcher(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    config = campaign_dispatcher_config(args)
    campaign = validate_campaign_worker_runtime(root, args.node, config)
    state_values = {
        **config,
        "mode": "campaign",
        "campaign_id": campaign["campaign_id"],
        "instance_id": args.instance_id,
    }
    lock_path = root / "dispatcher" / args.node / "dispatcher.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(f"campaign dispatcher already running for {args.node}")
        while True:
            if worker_stop_path(root, args.node).exists():
                update_dispatcher_state(
                    root, args.node, "stopped", stop_reason="break-glass", **state_values
                )
                return 0
            goal_path = campaign_goal_completed_path(root)
            if goal_path.exists():
                try:
                    goal = validate_goal_completed(root, campaign)
                except (OSError, ValueError) as error:
                    update_dispatcher_state(
                        root,
                        args.node,
                        "waiting-for-valid-goal-completion",
                        validation_error=str(error),
                        **state_values,
                    )
                    time.sleep(args.poll_interval)
                    continue
                update_dispatcher_state(
                    root,
                    args.node,
                    "goal-completed",
                    goal_completed_at=goal["created_at"],
                    final_fencing_epoch=goal["final_fencing_epoch"],
                    **state_values,
                )
                return 0
            if not campaign_active_attempt_path(root).exists():
                update_dispatcher_state(
                    root,
                    args.node,
                    "waiting-for-active-attempt",
                    **state_values,
                )
                time.sleep(args.poll_interval)
                continue
            try:
                attempt_root, attempt, active = active_attempt_record(root, campaign)
            except (OSError, ValueError) as error:
                update_dispatcher_state(
                    root,
                    args.node,
                    "waiting-for-active-attempt",
                    validation_error=str(error),
                    **state_values,
                )
                time.sleep(args.poll_interval)
                continue
            active_values = {
                "active_attempt_root": str(attempt_root),
                "active_experiment_id": attempt["experiment_id"],
                "active_attempt": attempt["attempt"],
                "active_launch_nonce": attempt["launch_nonce"],
                "active_fencing_epoch": attempt["fencing_epoch"],
            }
            if (attempt_root / "terminal.json").exists():
                update_dispatcher_state(
                    root,
                    args.node,
                    "watching",
                    active_attempt_terminal=True,
                    **active_values,
                    **state_values,
                )
                time.sleep(args.poll_interval)
                continue
            update_dispatcher_state(
                root,
                args.node,
                "watching",
                active_attempt_terminal=False,
                **active_values,
                **state_values,
            )
            dispatch_pending_once(
                attempt_root,
                attempt,
                args.node,
                config["thread_id"],
                Path(config["session_path"]) if config["session_path"] else None,
                config["codex_path"],
                Path(config["workdir"]),
                args.task_timeout,
                args.thread_quiet_seconds,
                args.thread_idle_timeout,
                dispatcher_root=root,
                agent_mode=config["agent_mode"],
                codex_home=config["codex_home"],
                codex_args=config["codex_args"],
            )
            time.sleep(args.poll_interval)


def update_campaign_supervisor_state(
    root: Path, node: str, status: str, **values: Any
) -> None:
    atomic_replace_json(
        campaign_supervisor_state_path(root, node),
        {
            "schema_version": SCHEMA_VERSION,
            "node": node,
            "hostname": short_hostname(),
            "pid": os.getpid(),
            "process_start_token": process_start_token(os.getpid()),
            "status": status,
            "heartbeat_at": timestamp(),
            **values,
        },
    )


def supervise_campaign_dispatcher(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    config = campaign_dispatcher_config(args)
    campaign = validate_campaign_worker_runtime(root, args.node, config)
    supervisor_values = {
        **config,
        "campaign_id": campaign["campaign_id"],
        "instance_id": args.instance_id,
    }
    lock_path = root / "supervisor" / args.node / "supervisor.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    child: subprocess.Popen[str] | None = None
    shutdown_requested = False

    def request_shutdown(_signum: int, _frame: Any) -> None:
        nonlocal shutdown_requested, child
        shutdown_requested = True
        if child is not None and child.poll() is None:
            child.terminate()

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)
    with lock_path.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(f"campaign supervisor already running for {args.node}")
        restart_count = 0
        while not shutdown_requested:
            if worker_stop_path(root, args.node).exists():
                update_campaign_supervisor_state(
                    root, args.node, "stopped", **supervisor_values
                )
                return 0
            if campaign_goal_completed_path(root).exists():
                try:
                    validate_goal_completed(root, campaign)
                except (OSError, ValueError) as error:
                    update_campaign_supervisor_state(
                        root,
                        args.node,
                        "waiting-for-valid-goal-completion",
                        validation_error=str(error),
                        **supervisor_values,
                    )
                    time.sleep(args.poll_interval)
                    continue
                else:
                    update_campaign_supervisor_state(
                        root, args.node, "goal-completed", **supervisor_values
                    )
                    return 0
            dispatcher_instance_id = uuid.uuid4().hex
            command = [
                sys.executable,
                str(Path(__file__).resolve()),
                "campaign-run",
                "--root",
                str(root),
                "--node",
                args.node,
                "--instance-id",
                dispatcher_instance_id,
                "--agent-mode",
                config["agent_mode"],
                "--workdir",
                config["workdir"],
                "--codex-path",
                config["codex_path"],
                "--poll-interval",
                str(args.poll_interval),
                "--task-timeout",
                str(args.task_timeout),
                "--thread-quiet-seconds",
                str(args.thread_quiet_seconds),
                "--thread-idle-timeout",
                str(args.thread_idle_timeout),
            ]
            if config["codex_home"]:
                command.extend(["--codex-home", config["codex_home"]])
            for value in config["codex_args"]:
                command.append(f"--codex-arg={value}")
            if config["agent_mode"] == "resume":
                command.extend(["--thread-id", config["thread_id"]])
                command.extend(["--session-path", config["session_path"]])
            child = subprocess.Popen(command, close_fds=True)
            update_campaign_supervisor_state(
                root,
                args.node,
                "supervising",
                dispatcher_pid=child.pid,
                dispatcher_instance_id=dispatcher_instance_id,
                restart_count=restart_count,
                **supervisor_values,
            )
            while child.poll() is None and not shutdown_requested:
                update_campaign_supervisor_state(
                    root,
                    args.node,
                    "supervising",
                    dispatcher_pid=child.pid,
                    dispatcher_instance_id=dispatcher_instance_id,
                    restart_count=restart_count,
                    **supervisor_values,
                )
                time.sleep(max(args.poll_interval, 0.1))
            if child.poll() is None:
                child.terminate()
            returncode = child.wait()
            child = None
            if shutdown_requested:
                break
            if campaign_goal_completed_path(root).exists():
                try:
                    validate_goal_completed(root, campaign)
                except (OSError, ValueError) as error:
                    update_campaign_supervisor_state(
                        root,
                        args.node,
                        "waiting-for-valid-goal-completion",
                        validation_error=str(error),
                        **supervisor_values,
                    )
                    time.sleep(args.poll_interval)
                    continue
                else:
                    update_campaign_supervisor_state(
                        root, args.node, "goal-completed", **supervisor_values
                    )
                    return 0
            if worker_stop_path(root, args.node).exists():
                update_campaign_supervisor_state(
                    root, args.node, "stopped", **supervisor_values
                )
                return 0
            restart_count += 1
            update_campaign_supervisor_state(
                root,
                args.node,
                "restarting",
                last_dispatcher_returncode=returncode,
                restart_count=restart_count,
                **supervisor_values,
            )
            time.sleep(args.restart_backoff)
    update_campaign_supervisor_state(
        root, args.node, "stopped", **supervisor_values
    )
    return 0


def start_campaign_dispatcher(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    config = campaign_dispatcher_config(args)
    campaign = validate_campaign_worker_runtime(root, args.node, config)
    if campaign_goal_completed_path(root).exists():
        validate_goal_completed(root, campaign)
        raise ValueError("campaign is already completed")
    supervisor_path = campaign_supervisor_state_path(root, args.node)
    state_path = dispatcher_state_path(root, args.node)
    requested = {**config, "campaign_id": campaign["campaign_id"]}
    if supervisor_path.exists():
        supervisor = read_json(supervisor_path)
        if campaign_supervisor_process_matches(supervisor, root, args.node):
            mismatched = [
                key for key, value in requested.items() if supervisor.get(key) != value
            ]
            if mismatched:
                raise ValueError(
                    "existing campaign supervisor has different configuration: "
                    + ", ".join(mismatched)
                )
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if not campaign_supervisor_process_matches(
                    supervisor, root, args.node
                ):
                    break
                if state_path.exists():
                    state = read_json(state_path)
                    if dispatcher_process_matches(state, root, args.node) and (
                        state.get("status") in ACTIVE_DISPATCHER_STATES
                    ) and (
                        state.get("instance_id")
                        == supervisor.get("dispatcher_instance_id")
                    ):
                        print(supervisor_path)
                        return 0
                time.sleep(0.2)
            raise TimeoutError(
                f"existing campaign supervisor did not expose a ready dispatcher: {supervisor_path}"
            )
    control_path = worker_control_lock_path(root, args.node)
    with control_path.open("a+", encoding="utf-8") as control_lock:
        fcntl.flock(control_lock, fcntl.LOCK_EX)
        worker_stop_path(root, args.node).unlink(missing_ok=True)
    log_path = root / "supervisor" / args.node / "supervisor.log"
    instance_id = uuid.uuid4().hex
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "campaign-supervise",
        "--root",
        str(root),
        "--node",
        args.node,
        "--instance-id",
        instance_id,
        "--agent-mode",
        config["agent_mode"],
        "--workdir",
        config["workdir"],
        "--codex-path",
        config["codex_path"],
        "--poll-interval",
        str(args.poll_interval),
        "--task-timeout",
        str(args.task_timeout),
        "--thread-quiet-seconds",
        str(args.thread_quiet_seconds),
        "--thread-idle-timeout",
        str(args.thread_idle_timeout),
        "--restart-backoff",
        str(args.restart_backoff),
    ]
    if config["codex_home"]:
        command.extend(["--codex-home", config["codex_home"]])
    for value in config["codex_args"]:
        command.append(f"--codex-arg={value}")
    if config["agent_mode"] == "resume":
        command.extend(["--thread-id", config["thread_id"]])
        command.extend(["--session-path", config["session_path"]])
    with log_path.open("a", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    _BACKGROUND_PROCESSES[process.pid] = process
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if supervisor_path.exists() and state_path.exists():
            supervisor = read_json(supervisor_path)
            state = read_json(state_path)
            if (
                supervisor.get("pid") == process.pid
                and supervisor.get("instance_id") == instance_id
                and campaign_supervisor_process_matches(
                    supervisor, root, args.node
                )
                and dispatcher_process_matches(state, root, args.node)
                and state.get("status") in ACTIVE_DISPATCHER_STATES
            ):
                print(supervisor_path)
                return 0
        if process.poll() is not None:
            raise RuntimeError(f"campaign supervisor exited; inspect {log_path}")
        time.sleep(0.2)
    raise TimeoutError(f"campaign dispatcher did not become ready; inspect {log_path}")


def status_campaign_dispatcher(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    campaign = load_campaign_manifest(root)
    expected_host = campaign["nodes"].get(args.node)
    if expected_host is None:
        raise ValueError(f"unknown campaign node: {args.node}")
    supervisor = read_json(campaign_supervisor_state_path(root, args.node))
    dispatcher = read_json(dispatcher_state_path(root, args.node))
    observed_host = short_hostname()
    if observed_host != expected_host:
        supervisor["process_alive"] = None
        dispatcher["process_alive"] = None
        payload = {
            "supervisor": supervisor,
            "dispatcher": dispatcher,
            "process_check": "unavailable-from-remote-host",
            "expected_host": expected_host,
            "observed_host": observed_host,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 2
    supervisor["process_alive"] = campaign_supervisor_process_matches(
        supervisor, root, args.node
    )
    dispatcher["process_alive"] = dispatcher_process_matches(
        dispatcher, root, args.node
    )
    payload = {"supervisor": supervisor, "dispatcher": dispatcher}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if supervisor["process_alive"] and dispatcher["process_alive"] else 1


def stop_campaign_dispatcher(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    campaign = load_campaign_manifest(root)
    expected_host = campaign["nodes"].get(args.node)
    if expected_host is None:
        raise ValueError(f"unknown campaign node: {args.node}")
    if short_hostname() != expected_host:
        raise ValueError(
            f"campaign-stop must run on {expected_host}, not {short_hostname()}"
        )
    supervisor_path = campaign_supervisor_state_path(root, args.node)
    supervisor = read_json(supervisor_path)
    control_path = worker_control_lock_path(root, args.node)
    with control_path.open("a+", encoding="utf-8") as control_lock:
        fcntl.flock(control_lock, fcntl.LOCK_EX)
        atomic_replace_json(
            worker_stop_path(root, args.node),
            {
                "schema_version": SCHEMA_VERSION,
                "kind": "break-glass-stop",
                "node": args.node,
                "supervisor_instance_id": supervisor.get("instance_id"),
                "created_at": timestamp(),
            },
        )
        if campaign_active_attempt_path(root).exists():
            try:
                attempt_root, _attempt, _active = active_attempt_record(
                    root, load_campaign_manifest(root)
                )
            except (OSError, ValueError):
                attempt_root = None
            if attempt_root is not None:
                for invocation_path in sorted(
                    (attempt_root / "invocations" / args.node).glob("*.json")
                ):
                    invocation = read_json(invocation_path)
                    request_id = str(invocation.get("request_id"))
                    if (attempt_root / "results" / args.node / f"{request_id}.json").exists():
                        continue
                    terminate_invocation(invocation, timeout=args.timeout)
        if campaign_supervisor_process_matches(supervisor, root, args.node):
            pid = int(supervisor["pid"])
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + args.timeout
            while process_alive(pid) and time.monotonic() < deadline:
                time.sleep(0.2)
            if process_alive(pid):
                os.killpg(pid, signal.SIGKILL)
    current = read_json(supervisor_path)
    current.update({"status": "stopped", "stopped_at": timestamp()})
    atomic_replace_json(supervisor_path, current)
    print(supervisor_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="publish an immutable bus manifest")
    init.add_argument("--root", required=True)
    init.add_argument("--authority-root", required=True)
    init.add_argument("--experiment-id", required=True)
    init.add_argument("--attempt", required=True)
    init.add_argument("--launch-nonce", required=True)
    init.add_argument("--science-contract-hash", required=True)
    init.add_argument("--fencing-epoch", type=int, required=True)
    init.add_argument("--coordinator-node", default="node0")
    init.add_argument("--coordinator-thread-id", required=True)
    init.add_argument("--node", action="append", type=parse_node, required=True)
    init.add_argument("--allow-host-mismatch", action="store_true", help=argparse.SUPPRESS)
    init.set_defaults(function=initialize_bus)

    campaign_init = subparsers.add_parser(
        "campaign-init", help="publish an immutable campaign manifest"
    )
    campaign_init.add_argument("--root", required=True)
    campaign_init.add_argument("--authority-root", required=True)
    campaign_init.add_argument("--attempts-root", required=True)
    campaign_init.add_argument("--campaign-id", required=True)
    campaign_init.add_argument("--science-contract-hash", required=True)
    campaign_init.add_argument("--coordinator-node", default="node0")
    campaign_init.add_argument("--coordinator-thread-id", required=True)
    campaign_init.add_argument(
        "--node", action="append", type=parse_node, required=True
    )
    campaign_init.add_argument(
        "--allow-host-mismatch", action="store_true", help=argparse.SUPPRESS
    )
    campaign_init.set_defaults(function=initialize_campaign)

    campaign_activate = subparsers.add_parser(
        "campaign-activate", help="atomically select the active attempt"
    )
    campaign_activate.add_argument("--root", required=True)
    campaign_activate.add_argument("--attempt-root", required=True)
    campaign_activate.add_argument("--expected-previous-epoch", type=int, required=True)
    campaign_activate.set_defaults(function=activate_campaign_attempt)

    campaign_complete = subparsers.add_parser(
        "campaign-complete", help="publish the fenced GOAL_COMPLETED record"
    )
    campaign_complete.add_argument("--root", required=True)
    campaign_complete.add_argument("--expected-attempt-root", required=True)
    campaign_complete.add_argument("--expected-attempt", required=True)
    campaign_complete.add_argument("--expected-launch-nonce", required=True)
    campaign_complete.add_argument("--expected-fencing-epoch", type=int, required=True)
    campaign_complete.add_argument("--summary", required=True)
    campaign_complete.add_argument("--evidence-path", action="append", default=[])
    campaign_complete.set_defaults(function=complete_campaign)

    publish = subparsers.add_parser("publish", help="publish one coordinator request")
    publish.add_argument("--root", required=True)
    publish.add_argument("--target", required=True)
    publish.add_argument("--action", required=True)
    message = publish.add_mutually_exclusive_group(required=True)
    message.add_argument("--message")
    message.add_argument("--message-file")
    publish.add_argument("--completion-predicate", required=True)
    publish.add_argument("--evidence-path", action="append", default=[])
    publish.add_argument("--request-id")
    publish.set_defaults(function=publish_request)

    close = subparsers.add_parser("close", help="close the bus after the objective ends")
    close.add_argument("--root", required=True)
    close.add_argument("--status", choices=("completed", "abandoned"), required=True)
    close.add_argument("--summary", required=True)
    close.set_defaults(function=close_bus)

    for command in ("start", "run"):
        dispatch = subparsers.add_parser(command)
        dispatch.add_argument("--root", required=True)
        dispatch.add_argument("--node", required=True)
        dispatch.add_argument(
            "--agent-mode", choices=sorted(AGENT_MODES), default="resume"
        )
        dispatch.add_argument("--thread-id")
        dispatch.add_argument("--instance-id", default=DEFAULT_INSTANCE_ID)
        dispatch.add_argument("--session-path")
        dispatch.add_argument("--workdir", required=True)
        dispatch.add_argument("--codex-path", default="codex")
        dispatch.add_argument("--codex-home")
        dispatch.add_argument("--codex-arg", action="append", default=[])
        dispatch.add_argument("--poll-interval", type=float, default=2.0)
        dispatch.add_argument("--task-timeout", type=int, default=7200)
        dispatch.add_argument("--thread-quiet-seconds", type=int, default=5)
        dispatch.add_argument("--thread-idle-timeout", type=int, default=21600)
        dispatch.set_defaults(function=start_dispatcher if command == "start" else run_dispatcher)

    for command in (
        "campaign-start",
        "campaign-run",
        "campaign-supervise",
    ):
        dispatch = subparsers.add_parser(command)
        dispatch.add_argument("--root", required=True)
        dispatch.add_argument("--node", required=True)
        dispatch.add_argument(
            "--agent-mode", choices=sorted(AGENT_MODES), default=DEFAULT_AGENT_MODE
        )
        dispatch.add_argument("--thread-id")
        dispatch.add_argument("--instance-id", default=DEFAULT_INSTANCE_ID)
        dispatch.add_argument("--session-path")
        dispatch.add_argument("--workdir", required=True)
        dispatch.add_argument("--codex-path", default="codex")
        dispatch.add_argument("--codex-home")
        dispatch.add_argument("--codex-arg", action="append", default=[])
        dispatch.add_argument("--poll-interval", type=float, default=2.0)
        dispatch.add_argument("--task-timeout", type=int, default=7200)
        dispatch.add_argument("--thread-quiet-seconds", type=int, default=5)
        dispatch.add_argument("--thread-idle-timeout", type=int, default=21600)
        dispatch.add_argument("--restart-backoff", type=float, default=2.0)
        functions = {
            "campaign-start": start_campaign_dispatcher,
            "campaign-run": run_campaign_dispatcher,
            "campaign-supervise": supervise_campaign_dispatcher,
        }
        dispatch.set_defaults(function=functions[command])

    status = subparsers.add_parser("status")
    status.add_argument("--root", required=True)
    status.add_argument("--node", required=True)
    status.set_defaults(function=status_dispatcher)

    stop = subparsers.add_parser("stop")
    stop.add_argument("--root", required=True)
    stop.add_argument("--node", required=True)
    stop.add_argument("--timeout", type=int, default=15)
    stop.set_defaults(function=stop_dispatcher)

    campaign_status = subparsers.add_parser("campaign-status")
    campaign_status.add_argument("--root", required=True)
    campaign_status.add_argument("--node", required=True)
    campaign_status.set_defaults(function=status_campaign_dispatcher)

    campaign_stop = subparsers.add_parser("campaign-stop")
    campaign_stop.add_argument("--root", required=True)
    campaign_stop.add_argument("--node", required=True)
    campaign_stop.add_argument("--timeout", type=int, default=15)
    campaign_stop.set_defaults(function=stop_campaign_dispatcher)

    helper = subparsers.add_parser("_resume-helper", help=argparse.SUPPRESS)
    helper.add_argument("--spec", required=True)
    helper.set_defaults(function=resume_helper)

    launcher = subparsers.add_parser("_codex-launcher", help=argparse.SUPPRESS)
    launcher.add_argument("--spec", required=True)
    launcher.set_defaults(function=codex_launcher)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.function(args))
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
