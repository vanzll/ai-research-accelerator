#!/usr/bin/env python3
"""Token-free watcher that wakes an agent only for declared task events."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
DEFAULT_FATAL_PATTERNS = [
    r"Traceback \(most recent call last\):",
    r"CUDA out of memory",
    r"OutOfMemoryError",
    r"Segmentation fault",
    r"NCCL[^\n]*(?:error|failed|timeout)",
]
TERMINAL_STATES = {
    "acknowledged",
    "cancelled",
    "duplicate-event-suppressed",
    "notified",
    "notified-unconfirmed",
    "wake-failed",
}
_BACKGROUND_PROCESSES: dict[int, subprocess.Popen[str]] = {}


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def timestamp(value: dt.datetime | None = None) -> str:
    return (value or utc_now()).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = timestamp()
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def load_state(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"relay state must be a JSON object: {path}")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported relay schema {value.get('schema_version')!r}; "
            f"expected {SCHEMA_VERSION}"
        )
    return value


def tail_text(path: Path, limit: int) -> str:
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(size - limit, 0))
        return handle.read().decode("utf-8", errors="replace")


def nested_get(value: Any, dotted_key: str) -> Any:
    current = value
    for component in dotted_key.split("."):
        if not isinstance(current, dict) or component not in current:
            raise KeyError(dotted_key)
        current = current[component]
    return current


def process_alive(pid: int) -> bool:
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
    try:
        completed = subprocess.run(
            ["ps", "-o", "stat=", "-p", str(pid)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True
    status = completed.stdout.strip()
    return completed.returncode == 0 and bool(status) and not status.startswith("Z")


def tmux_alive(session: str) -> bool:
    try:
        completed = subprocess.run(
            ["tmux", "has-session", "-t", session],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def regex_excerpt(text: str, match: re.Match[str], limit: int = 1200) -> str:
    start = max(match.start() - limit // 4, 0)
    end = min(match.end() + 3 * limit // 4, len(text))
    return text[start:end].strip()[-limit:]


def first_pattern_match(patterns: list[str], text: str) -> tuple[str, re.Match[str]] | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return pattern, match
    return None


def progress_from_log(text: str, regex: str) -> float | None:
    values: list[float] = []
    for match in re.finditer(regex, text, re.MULTILINE):
        raw = match.groupdict().get("value")
        if raw is None:
            if match.lastindex is None:
                raise ValueError("progress regex needs a capture group or named group 'value'")
            raw = match.group(1)
        try:
            values.append(float(raw))
        except (TypeError, ValueError):
            continue
    return max(values) if values else None


def progress_from_json(path: Path, key: str) -> float | None:
    if not path.exists():
        return None
    try:
        value = nested_get(json.loads(path.read_text(encoding="utf-8")), key)
        return float(value)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def observe(state: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    monitor = state["monitor"]
    now = utc_now()
    observation: dict[str, Any] = {
        "checked_at": timestamp(now),
        "progress": state.get("last_observation", {}).get("progress"),
    }

    pid = monitor.get("pid")
    if pid is not None:
        observation["pid"] = int(pid)
        observation["process_alive"] = process_alive(int(pid))

    tmux_session = monitor.get("tmux_session")
    if tmux_session:
        observation["tmux_session"] = str(tmux_session)
        observation["tmux_alive"] = tmux_alive(str(tmux_session))

    failure_markers = [
        str(Path(path)) for path in monitor.get("failure_markers", []) if Path(path).exists()
    ]
    success_markers = [
        str(Path(path)) for path in monitor.get("success_markers", []) if Path(path).exists()
    ]
    observation["failure_markers"] = failure_markers
    observation["success_markers"] = success_markers

    log_text = ""
    log_path_value = monitor.get("log_path")
    if log_path_value:
        log_path = Path(log_path_value)
        observation["log_path"] = str(log_path)
        observation["log_exists"] = log_path.exists()
        if log_path.exists():
            stat = log_path.stat()
            observation["log_size"] = stat.st_size
            observation["log_mtime"] = timestamp(
                dt.datetime.fromtimestamp(stat.st_mtime, dt.timezone.utc)
            )
            observation["log_age_seconds"] = max(now.timestamp() - stat.st_mtime, 0.0)
            log_text = ANSI_RE.sub(
                "", tail_text(log_path, int(monitor.get("tail_bytes", 2 * 1024 * 1024)))
            )

    progress = monitor.get("progress")
    if progress:
        value = None
        if progress.get("source") == "log" and log_text:
            value = progress_from_log(log_text, str(progress["regex"]))
        elif progress.get("source") == "json":
            value = progress_from_json(Path(progress["path"]), str(progress["key"]))
        if value is not None:
            previous = observation.get("progress")
            observation["progress"] = value if previous is None else max(float(previous), value)
        observation["target"] = float(progress["target"])

    fatal = first_pattern_match(list(monitor.get("fatal_patterns", [])), log_text)
    if fatal:
        pattern, match = fatal
        observation["fatal_pattern"] = pattern
        observation["fatal_excerpt"] = regex_excerpt(log_text, match)

    success = first_pattern_match(list(monitor.get("success_patterns", [])), log_text)
    if success:
        pattern, match = success
        observation["success_pattern"] = pattern
        observation["success_excerpt"] = regex_excerpt(log_text, match, limit=600)

    reason = None
    if failure_markers:
        reason = "failure-marker"
    elif fatal:
        reason = "fatal-log-pattern"
    elif success_markers:
        reason = "success-marker"
    elif success:
        reason = "success-log-pattern"
    elif progress and observation.get("progress") is not None:
        if float(observation["progress"]) >= float(progress["target"]):
            reason = "progress-target-reached"

    if reason is None and pid is not None and not observation["process_alive"]:
        reason = "process-exited"
    if reason is None and tmux_session and not observation["tmux_alive"]:
        reason = "tmux-exited"

    if reason is None and log_path_value:
        stale_after = monitor.get("stale_after_seconds")
        if observation.get("log_exists") and stale_after is not None:
            if observation["log_age_seconds"] >= float(stale_after):
                reason = "log-stale"
        elif not observation.get("log_exists"):
            missing_after = monitor.get("missing_log_after_seconds")
            if missing_after is not None:
                age = max((now - parse_timestamp(state["created_at"])).total_seconds(), 0.0)
                observation["relay_age_seconds"] = age
                if age >= float(missing_after):
                    reason = "log-missing"

    return observation, reason


def make_event(
    state: dict[str, Any], reason: str, observation: dict[str, Any]
) -> dict[str, Any]:
    material = f"{state['name']}|{state['generation']}|{reason}"
    return {
        "id": hashlib.sha256(material.encode("utf-8")).hexdigest()[:16],
        "reason": reason,
        "generation": state["generation"],
        "created_at": timestamp(),
        "attempts": 0,
        "delivery": "pending",
        "observation": observation,
    }


def compact_observation(observation: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "checked_at",
        "progress",
        "target",
        "pid",
        "process_alive",
        "tmux_session",
        "tmux_alive",
        "log_path",
        "log_exists",
        "log_age_seconds",
        "failure_markers",
        "success_markers",
        "fatal_pattern",
        "fatal_excerpt",
        "success_pattern",
        "success_excerpt",
    ]
    return {key: observation[key] for key in keys if key in observation}


def event_prompt(state: dict[str, Any], event: dict[str, Any]) -> str:
    delivery = state["delivery"]
    lines = [
        f"Long-task relay event (event_id={event['id']})",
        f"Reason: {event['reason']}",
        f"Task: {state['name']}",
        f"Generation: {state['generation']}",
        f"Repository/workdir: {state.get('repo_path', '')}",
        f"State: {state['state_path']}",
        "Evidence:",
        json.dumps(compact_observation(event["observation"]), indent=2, sort_keys=True),
    ]
    context_paths = state.get("context_paths", [])
    if context_paths:
        lines.append("Context paths: " + ", ".join(context_paths))
    instructions = delivery.get("wake_instructions")
    if instructions:
        lines.extend(["Agent instructions:", str(instructions)])
    lines.append(
        "This is a mechanical notification. Verify primary evidence, handle one event, "
        "then acknowledge and re-arm only if further waiting is required."
    )
    return "\n".join(lines) + "\n"


def thread_idle_observation(state: dict[str, Any]) -> dict[str, Any]:
    session_path = state["delivery"].get("session_path")
    if not session_path:
        return {"idle": True, "check": "skipped-no-session-path"}
    path = Path(session_path)
    if not path.exists():
        raise FileNotFoundError(f"agent session transcript not found: {path}")

    latest_lifecycle = None
    latest_turn_id = None
    for line in tail_text(path, 4 * 1024 * 1024).splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("type") != "event_msg":
            continue
        payload = record.get("payload", {})
        if payload.get("type") in {"task_started", "task_complete"}:
            latest_lifecycle = payload["type"]
            latest_turn_id = payload.get("turn_id")

    quiet_seconds = max(time.time() - path.stat().st_mtime, 0.0)
    required_quiet = int(state["delivery"].get("thread_quiet_seconds", 15))
    return {
        "session_path": str(path),
        "latest_lifecycle": latest_lifecycle,
        "latest_turn_id": latest_turn_id,
        "quiet_seconds": quiet_seconds,
        "required_quiet_seconds": required_quiet,
        "idle": latest_lifecycle == "task_complete" and quiet_seconds >= required_quiet,
    }


def wait_for_thread_idle(state: dict[str, Any], state_path: Path) -> bool:
    event = state["pending_event"]
    deadline = time.monotonic() + int(
        state["delivery"].get("thread_idle_timeout_seconds", 21600)
    )
    while True:
        try:
            observation = thread_idle_observation(state)
        except (OSError, ValueError) as error:
            event["delivery"] = "thread-idle-check-failed"
            event["thread_idle_error"] = str(error)
            atomic_write_json(state_path, state)
            return False
        event["delivery"] = "waiting-for-thread-idle"
        event["thread_idle_observation"] = observation
        atomic_write_json(state_path, state)
        if observation["idle"]:
            return True
        if time.monotonic() >= deadline:
            event["delivery"] = "thread-idle-timeout"
            atomic_write_json(state_path, state)
            return False
        time.sleep(int(state["delivery"].get("thread_idle_poll_seconds", 5)))


def tui_pane_info(pane: str) -> dict[str, Any]:
    completed = subprocess.run(
        [
            "tmux",
            "display-message",
            "-pt",
            pane,
            "#{pane_id}\t#{pane_pid}\t#{pane_current_command}",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout.strip() or f"tmux pane not found: {pane}")
    pane_id, pane_pid, command = completed.stdout.strip().split("\t", 2)
    return {"pane_id": pane_id, "pane_pid": int(pane_pid), "command": command}


def tui_acknowledged(observation: dict[str, Any], previous_turn_id: str | None) -> bool:
    return (
        observation.get("latest_lifecycle") == "task_started"
        and observation.get("latest_turn_id") != previous_turn_id
    )


def deliver_to_tui(state: dict[str, Any], state_path: Path) -> bool:
    delivery = state["delivery"]
    event = state["pending_event"]
    pane = str(delivery["tui_pane"])
    info = tui_pane_info(pane)
    expected_command = str(delivery.get("expected_pane_command", "codex"))
    if info["command"] != expected_command:
        raise RuntimeError(
            f"refusing injection: pane runs {info['command']!r}, expected {expected_command!r}"
        )
    expected_pid = delivery.get("tui_pane_pid")
    if expected_pid is not None and info["pane_pid"] != int(expected_pid):
        raise RuntimeError(
            f"refusing injection: pane pid changed from {expected_pid} to {info['pane_pid']}"
        )

    event["attempts"] += 1
    event["last_attempt_at"] = timestamp()
    event["delivery"] = "injecting-into-tui"
    event["tui_pane_info"] = info
    previous_turn_id = event.get("thread_idle_observation", {}).get("latest_turn_id")
    atomic_write_json(state_path, state)

    buffer_name = "relay_" + re.sub(r"[^A-Za-z0-9_]", "_", event["id"])
    loaded = subprocess.run(
        ["tmux", "load-buffer", "-b", buffer_name, "-"],
        input=event_prompt(state, event),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
        check=False,
    )
    if loaded.returncode != 0:
        raise RuntimeError(loaded.stdout.strip() or "tmux load-buffer failed")
    pasted = subprocess.run(
        ["tmux", "paste-buffer", "-b", buffer_name, "-t", pane, "-d"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
        check=False,
    )
    if pasted.returncode != 0:
        raise RuntimeError(pasted.stdout.strip() or "tmux paste-buffer failed")

    event["delivery"] = "injected-awaiting-ack"
    event["injected_at"] = timestamp()
    atomic_write_json(state_path, state)
    time.sleep(float(delivery.get("tui_paste_settle_seconds", 1.5)))

    max_submits = int(delivery.get("tui_submit_attempts", 3))
    ack_wait = float(delivery.get("tui_submit_ack_wait_seconds", 5))
    for submit_index in range(1, max_submits + 1):
        submitted = subprocess.run(
            ["tmux", "send-keys", "-t", pane, "Enter"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
            check=False,
        )
        if submitted.returncode != 0:
            raise RuntimeError(submitted.stdout.strip() or "tmux send-keys failed")
        event["tui_submit_count"] = submit_index
        event["last_submit_at"] = timestamp()
        atomic_write_json(state_path, state)

        if not delivery.get("session_path"):
            event["delivery"] = "sent-unconfirmed"
            state["status"] = "notified-unconfirmed"
            return True

        deadline = time.monotonic() + ack_wait
        while time.monotonic() < deadline:
            observation = thread_idle_observation(state)
            event["tui_ack_observation"] = observation
            if tui_acknowledged(observation, previous_turn_id):
                event["delivery"] = "sent"
                event["sent_at"] = timestamp()
                event["ack_turn_id"] = observation["latest_turn_id"]
                state["status"] = "notified"
                return True
            atomic_write_json(state_path, state)
            time.sleep(0.25)

    event["delivery"] = "injected-unconfirmed"
    state["status"] = "notified-unconfirmed"
    return True


def delivery_command(state: dict[str, Any]) -> list[str]:
    delivery = state["delivery"]
    mode = delivery["mode"]
    if mode == "codex-resume":
        return [
            str(delivery.get("codex_path", "codex")),
            "exec",
            "resume",
            str(delivery["thread_id"]),
            "-",
        ]
    if mode == "command":
        command = delivery.get("command")
        if not isinstance(command, list) or not command or not all(
            isinstance(item, str) and item for item in command
        ):
            raise ValueError("command delivery requires a non-empty string argv list")
        return command
    raise ValueError(f"delivery mode has no command adapter: {mode}")


def deliver(state: dict[str, Any], state_path: Path, no_wake: bool = False) -> bool:
    event = state["pending_event"]
    delivery = state["delivery"]
    mode = delivery["mode"]
    if no_wake:
        event["delivery"] = "suppressed-for-dry-run"
        state["status"] = "notified"
        return True

    if mode == "inbox":
        inbox_path = Path(delivery["inbox_path"])
        inbox_path.parent.mkdir(parents=True, exist_ok=True)
        inbox_path.write_text(event_prompt(state, event), encoding="utf-8")
        event["delivery"] = "written-to-inbox"
        event["sent_at"] = timestamp()
        event["inbox_path"] = str(inbox_path)
        state["status"] = "notified"
        return True

    if not wait_for_thread_idle(state, state_path):
        return False

    if mode == "tui-send-keys":
        try:
            return deliver_to_tui(state, state_path)
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
            event["delivery"] = "tui-injection-failed"
            event["last_error"] = str(error)
            return False

    event["attempts"] += 1
    event["last_attempt_at"] = timestamp()
    event["delivery"] = "in-flight"
    command = delivery_command(state)
    event["command"] = command
    atomic_write_json(state_path, state)
    try:
        completed = subprocess.run(
            command,
            input=event_prompt(state, event),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=int(delivery.get("wake_timeout_seconds", 21600)),
            check=False,
            env=os.environ.copy(),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        event["last_returncode"] = "timeout" if isinstance(
            error, subprocess.TimeoutExpired
        ) else "os-error"
        output = getattr(error, "stdout", "") or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        event["last_output_tail"] = str(output)[-2000:]
        event["last_error"] = str(error)
        event["delivery"] = "pending-retry"
        return False

    event["last_returncode"] = completed.returncode
    event["last_output_tail"] = completed.stdout[-2000:]
    if completed.returncode == 0:
        event["delivery"] = "sent"
        event["sent_at"] = timestamp()
        state["status"] = "notified"
        return True
    event["delivery"] = "pending-retry"
    return False


def _run_locked(state_path: Path, once: bool, no_wake: bool) -> int:
    state = load_state(state_path)
    state["watcher_pid"] = os.getpid()
    state["watcher_started_at"] = timestamp()
    state["status"] = "watching"
    atomic_write_json(state_path, state)

    while True:
        state = load_state(state_path)
        if state.get("status") == "cancel-requested":
            state["status"] = "cancelled"
            atomic_write_json(state_path, state)
            return 0
        if state.get("status") in TERMINAL_STATES:
            return 0

        observation, reason = observe(state)
        state["last_observation"] = observation
        state["last_observation_reason"] = reason
        if reason and not state.get("pending_event"):
            state["pending_event"] = make_event(state, reason, observation)
            state["status"] = "event-pending"

        event = state.get("pending_event")
        if event and event["id"] in state.get("sent_event_ids", []):
            state["status"] = "duplicate-event-suppressed"
            atomic_write_json(state_path, state)
            return 0

        atomic_write_json(state_path, state)
        if event:
            success = deliver(state, state_path, no_wake=no_wake)
            if success:
                state.setdefault("sent_event_ids", []).append(event["id"])
                atomic_write_json(state_path, state)
                return 0
            event["failed_delivery_cycles"] = int(event.get("failed_delivery_cycles", 0)) + 1
            atomic_write_json(state_path, state)
            failed_cycles = int(event["failed_delivery_cycles"])
            if failed_cycles >= int(state["delivery"].get("max_wake_attempts", 5)):
                state["status"] = "wake-failed"
                atomic_write_json(state_path, state)
                return 1
            time.sleep(min(60 * (2 ** max(failed_cycles - 1, 0)), 600))
            continue

        if once:
            return 0
        time.sleep(int(state["monitor"].get("poll_interval_seconds", 120)))


def run_watcher(state_path: Path, once: bool = False, no_wake: bool = False) -> int:
    state_path = state_path.resolve()
    lock_path = state_path.with_suffix(state_path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("another watcher owns the state lock", file=sys.stderr)
            return 2
        try:
            return _run_locked(state_path, once=once, no_wake=no_wake)
        finally:
            try:
                state = load_state(state_path)
                if state.get("watcher_pid") == os.getpid():
                    state["watcher_pid"] = None
                    state["watcher_exited_at"] = timestamp()
                    atomic_write_json(state_path, state)
            except (OSError, ValueError, json.JSONDecodeError):
                pass


def absolute_path(value: str | None) -> str | None:
    return str(Path(value).expanduser().resolve()) if value else None


def build_state(args: argparse.Namespace, state_path: Path) -> dict[str, Any]:
    if state_path.exists() and not args.force:
        raise ValueError(f"state already exists; use rearm or --force: {state_path}")
    if state_path.exists():
        old = load_state(state_path)
        old_pid = old.get("watcher_pid")
        if old_pid and process_alive(int(old_pid)):
            raise ValueError(f"refusing to replace state owned by live watcher pid {old_pid}")

    progress = None
    if args.progress_regex:
        if args.target is None:
            raise ValueError("--progress-regex requires --target")
        re.compile(args.progress_regex)
        progress = {
            "source": "log",
            "regex": args.progress_regex,
            "target": args.target,
        }
    elif args.progress_json or args.progress_key:
        if not (args.progress_json and args.progress_key and args.target is not None):
            raise ValueError("JSON progress requires --progress-json, --progress-key, and --target")
        progress = {
            "source": "json",
            "path": absolute_path(args.progress_json),
            "key": args.progress_key,
            "target": args.target,
        }

    fatal_patterns = list(args.fatal_pattern or [])
    if not args.no_default_fatal_patterns:
        fatal_patterns = DEFAULT_FATAL_PATTERNS + fatal_patterns
    for pattern in fatal_patterns + list(args.success_pattern or []):
        re.compile(pattern)

    monitor = {
        "log_path": absolute_path(args.log),
        "pid": args.pid,
        "tmux_session": args.tmux_session,
        "progress": progress,
        "success_markers": [absolute_path(path) for path in args.success_marker or []],
        "failure_markers": [absolute_path(path) for path in args.failure_marker or []],
        "success_patterns": list(args.success_pattern or []),
        "fatal_patterns": fatal_patterns,
        "stale_after_seconds": args.stale_after,
        "missing_log_after_seconds": args.missing_log_after,
        "poll_interval_seconds": args.poll_interval,
        "tail_bytes": args.tail_bytes,
    }
    if not any(
        [
            monitor["log_path"],
            monitor["pid"],
            monitor["tmux_session"],
            monitor["success_markers"],
            monitor["failure_markers"],
            progress,
        ]
    ):
        raise ValueError("configure at least one monitor source")

    mode = args.delivery_mode
    delivery: dict[str, Any] = {
        "mode": mode,
        "session_path": absolute_path(args.session_path),
        "thread_quiet_seconds": args.thread_quiet_seconds,
        "thread_idle_timeout_seconds": args.thread_idle_timeout,
        "thread_idle_poll_seconds": args.thread_idle_poll,
        "wake_timeout_seconds": args.wake_timeout,
        "max_wake_attempts": args.max_wake_attempts,
        "wake_instructions": args.wake_instructions,
    }
    if mode == "codex-resume":
        thread_id = args.thread_id or os.environ.get("CODEX_THREAD_ID")
        if not thread_id:
            raise ValueError("codex-resume requires --thread-id or CODEX_THREAD_ID")
        delivery["thread_id"] = thread_id
        delivery["codex_path"] = args.codex_path or shutil.which("codex") or "codex"
    elif mode == "command":
        if not args.delivery_command_json:
            raise ValueError("command delivery requires --delivery-command-json")
        command = json.loads(args.delivery_command_json)
        if not isinstance(command, list) or not command or not all(
            isinstance(item, str) and item for item in command
        ):
            raise ValueError("--delivery-command-json must be a JSON string array")
        delivery["command"] = command
    elif mode == "tui-send-keys":
        if not args.tui_pane:
            raise ValueError("tui-send-keys requires --tui-pane")
        delivery.update(
            {
                "tui_pane": args.tui_pane,
                "tui_pane_pid": args.tui_pane_pid,
                "expected_pane_command": args.expected_pane_command,
                "tui_paste_settle_seconds": args.tui_paste_settle_seconds,
                "tui_submit_attempts": args.tui_submit_attempts,
                "tui_submit_ack_wait_seconds": args.tui_submit_ack_wait_seconds,
            }
        )
    elif mode == "inbox":
        delivery["inbox_path"] = absolute_path(
            args.inbox_path or str(state_path.with_suffix(state_path.suffix + ".event.txt"))
        )

    now = timestamp()
    return {
        "schema_version": SCHEMA_VERSION,
        "name": args.name,
        "generation": 1,
        "created_at": now,
        "updated_at": now,
        "repo_path": absolute_path(args.repo_path or os.getcwd()),
        "state_path": str(state_path),
        "context_paths": [absolute_path(path) for path in args.context_path or []],
        "monitor": monitor,
        "delivery": delivery,
        "status": "armed",
        "watcher_pid": None,
        "pending_event": None,
        "sent_event_ids": [],
        "event_history": [],
    }


def start_background(state_path: Path, watcher_log: str | None = None) -> int:
    log_path = Path(
        watcher_log or str(state_path.with_suffix(state_path.suffix + ".watcher.log"))
    ).expanduser().resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    state = load_state(state_path)
    state["watcher_log"] = str(log_path)
    atomic_write_json(state_path, state)
    with log_path.open("a", encoding="utf-8") as output:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "run", "--state", str(state_path)],
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    _BACKGROUND_PROCESSES[process.pid] = process
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        state = load_state(state_path)
        if state.get("status") == "watching" and state.get("watcher_pid") == process.pid:
            return process.pid
        if state.get("status") in TERMINAL_STATES and process.poll() is not None:
            return process.pid
        if process.poll() is not None:
            raise RuntimeError(f"watcher exited during bootstrap with status {process.returncode}")
        time.sleep(0.1)
    process.terminate()
    raise RuntimeError("watcher did not establish a watching heartbeat within 8 seconds")


def command_arm(args: argparse.Namespace) -> int:
    state_path = Path(args.state).expanduser().resolve()
    state = build_state(args, state_path)
    atomic_write_json(state_path, state)
    if args.background:
        start_background(state_path, args.watcher_log)
        print(json.dumps(status_payload(state_path), indent=2, sort_keys=True))
        return 0
    return run_watcher(state_path)


def status_payload(state_path: Path) -> dict[str, Any]:
    state = load_state(state_path)
    watcher_pid = state.get("watcher_pid")
    return {
        "name": state["name"],
        "generation": state["generation"],
        "status": state["status"],
        "state_path": str(state_path),
        "watcher_pid": watcher_pid,
        "watcher_alive": bool(watcher_pid and process_alive(int(watcher_pid))),
        "last_observation": state.get("last_observation"),
        "pending_event": state.get("pending_event"),
        "watcher_log": state.get("watcher_log"),
    }


def command_status(args: argparse.Namespace) -> int:
    print(json.dumps(status_payload(Path(args.state).expanduser().resolve()), indent=2, sort_keys=True))
    return 0


def command_acknowledge(args: argparse.Namespace) -> int:
    state_path = Path(args.state).expanduser().resolve()
    state = load_state(state_path)
    event = state.get("pending_event")
    if event:
        event["acknowledged_at"] = timestamp()
        event["acknowledgement"] = args.note
        state.setdefault("event_history", []).append(event)
    state["pending_event"] = None
    state["status"] = "acknowledged"
    atomic_write_json(state_path, state)
    return 0


def command_rearm(args: argparse.Namespace) -> int:
    state_path = Path(args.state).expanduser().resolve()
    state = load_state(state_path)
    watcher_pid = state.get("watcher_pid")
    if watcher_pid and process_alive(int(watcher_pid)):
        raise ValueError(f"cannot rearm while watcher pid {watcher_pid} is alive")
    event = state.get("pending_event")
    if event:
        state.setdefault("event_history", []).append(event)
    state["pending_event"] = None
    state["generation"] = int(state.get("generation", 0)) + 1
    state["status"] = "armed"
    state["watcher_pid"] = None
    if args.target is not None:
        progress = state["monitor"].get("progress")
        if not progress:
            raise ValueError("cannot set target: relay has no progress monitor")
        progress["target"] = args.target
    if args.wake_instructions is not None:
        state["delivery"]["wake_instructions"] = args.wake_instructions
    atomic_write_json(state_path, state)
    if args.background:
        start_background(state_path, args.watcher_log)
        print(json.dumps(status_payload(state_path), indent=2, sort_keys=True))
        return 0
    return run_watcher(state_path)


def command_cancel(args: argparse.Namespace) -> int:
    state_path = Path(args.state).expanduser().resolve()
    state = load_state(state_path)
    watcher_pid = state.get("watcher_pid")
    state["status"] = "cancel-requested" if watcher_pid else "cancelled"
    state["cancel_requested_at"] = timestamp()
    atomic_write_json(state_path, state)
    return 0


def command_test_event(args: argparse.Namespace) -> int:
    state_path = Path(args.state).expanduser().resolve()
    state = load_state(state_path)
    watcher_pid = state.get("watcher_pid")
    if watcher_pid and process_alive(int(watcher_pid)):
        raise ValueError(f"cannot inject test event while watcher pid {watcher_pid} is alive")
    observation, _ = observe(state)
    state["pending_event"] = make_event(state, args.reason, observation)
    state["status"] = "event-pending"
    atomic_write_json(state_path, state)
    if args.deliver:
        success = deliver(state, state_path, no_wake=args.no_wake)
        if success:
            state.setdefault("sent_event_ids", []).append(state["pending_event"]["id"])
        atomic_write_json(state_path, state)
        return 0 if success else 1
    print(event_prompt(state, state["pending_event"]), end="")
    return 0


def add_state_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--state", required=True, help="Durable relay JSON state path")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    arm = subparsers.add_parser("arm", help="Create relay state and start watching")
    add_state_argument(arm)
    arm.add_argument("--name", required=True)
    arm.add_argument("--repo-path")
    arm.add_argument("--log")
    arm.add_argument("--pid", type=int)
    arm.add_argument("--tmux-session")
    arm.add_argument("--progress-regex")
    arm.add_argument("--progress-json")
    arm.add_argument("--progress-key")
    arm.add_argument("--target", type=float)
    arm.add_argument("--success-marker", action="append")
    arm.add_argument("--failure-marker", action="append")
    arm.add_argument("--success-pattern", action="append")
    arm.add_argument("--fatal-pattern", action="append")
    arm.add_argument("--no-default-fatal-patterns", action="store_true")
    arm.add_argument("--stale-after", type=float)
    arm.add_argument("--missing-log-after", type=float)
    arm.add_argument("--poll-interval", type=int, default=120)
    arm.add_argument("--tail-bytes", type=int, default=2 * 1024 * 1024)
    arm.add_argument(
        "--delivery-mode",
        choices=["codex-resume", "command", "tui-send-keys", "inbox"],
        default="inbox",
    )
    arm.add_argument("--codex-path")
    arm.add_argument("--thread-id")
    arm.add_argument("--session-path")
    arm.add_argument("--delivery-command-json")
    arm.add_argument("--tui-pane")
    arm.add_argument("--tui-pane-pid", type=int)
    arm.add_argument("--expected-pane-command", default="codex")
    arm.add_argument("--tui-paste-settle-seconds", type=float, default=1.5)
    arm.add_argument("--tui-submit-attempts", type=int, default=3)
    arm.add_argument("--tui-submit-ack-wait-seconds", type=float, default=5)
    arm.add_argument("--inbox-path")
    arm.add_argument("--wake-instructions")
    arm.add_argument("--context-path", action="append")
    arm.add_argument("--thread-quiet-seconds", type=int, default=15)
    arm.add_argument("--thread-idle-timeout", type=int, default=21600)
    arm.add_argument("--thread-idle-poll", type=int, default=5)
    arm.add_argument("--wake-timeout", type=int, default=21600)
    arm.add_argument("--max-wake-attempts", type=int, default=5)
    arm.add_argument("--background", action="store_true")
    arm.add_argument("--watcher-log")
    arm.add_argument("--force", action="store_true")
    arm.set_defaults(func=command_arm)

    run = subparsers.add_parser("run", help="Run a configured watcher")
    add_state_argument(run)
    run.add_argument("--once", action="store_true")
    run.add_argument("--no-wake", action="store_true")
    run.set_defaults(
        func=lambda args: run_watcher(
            Path(args.state).expanduser().resolve(), once=args.once, no_wake=args.no_wake
        )
    )

    status = subparsers.add_parser("status", help="Print compact relay status")
    add_state_argument(status)
    status.set_defaults(func=command_status)

    acknowledge = subparsers.add_parser("acknowledge", help="Record event handling")
    add_state_argument(acknowledge)
    acknowledge.add_argument("--note", default="handled by agent")
    acknowledge.set_defaults(func=command_acknowledge)

    rearm = subparsers.add_parser("rearm", help="Start a new event generation")
    add_state_argument(rearm)
    rearm.add_argument("--target", type=float)
    rearm.add_argument("--wake-instructions")
    rearm.add_argument("--background", action="store_true")
    rearm.add_argument("--watcher-log")
    rearm.set_defaults(func=command_rearm)

    cancel = subparsers.add_parser("cancel", help="Request watcher cancellation")
    add_state_argument(cancel)
    cancel.set_defaults(func=command_cancel)

    test_event = subparsers.add_parser("test-event", help="Create a synthetic relay event")
    add_state_argument(test_event)
    test_event.add_argument("--reason", default="manual-test")
    test_event.add_argument("--deliver", action="store_true")
    test_event.add_argument("--no-wake", action="store_true")
    test_event.set_defaults(func=command_test_event)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"relay error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
