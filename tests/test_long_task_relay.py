from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "ai-research-accelerator"
    / "skills"
    / "long-task-relay"
    / "scripts"
    / "long_task_relay.py"
)
SPEC = importlib.util.spec_from_file_location("long_task_relay", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def relay_state(directory: str) -> tuple[Path, dict]:
    root = Path(directory)
    state_path = root / "relay.json"
    log_path = root / "task.log"
    state = {
        "schema_version": 1,
        "name": "test-task",
        "generation": 1,
        "created_at": MODULE.timestamp(),
        "updated_at": MODULE.timestamp(),
        "repo_path": str(root),
        "state_path": str(state_path),
        "context_paths": [],
        "monitor": {
            "log_path": str(log_path),
            "pid": None,
            "tmux_session": None,
            "progress": None,
            "success_markers": [],
            "failure_markers": [],
            "success_patterns": [],
            "fatal_patterns": [],
            "stale_after_seconds": None,
            "missing_log_after_seconds": None,
            "poll_interval_seconds": 1,
            "tail_bytes": 1024 * 1024,
        },
        "delivery": {
            "mode": "inbox",
            "inbox_path": str(root / "event.txt"),
            "session_path": None,
            "max_wake_attempts": 3,
            "wake_instructions": "Inspect the task.",
        },
        "status": "armed",
        "watcher_pid": None,
        "pending_event": None,
        "sent_event_ids": [],
        "event_history": [],
    }
    return state_path, state


class RelayObservationTests(unittest.TestCase):
    def test_progress_target_is_extracted_from_log(self):
        with tempfile.TemporaryDirectory() as directory:
            _, state = relay_state(directory)
            Path(state["monitor"]["log_path"]).write_text(
                "step=3\nstep=9\n", encoding="utf-8"
            )
            state["monitor"]["progress"] = {
                "source": "log",
                "regex": r"step=(\d+)",
                "target": 8,
            }
            observation, reason = MODULE.observe(state)
            self.assertEqual(observation["progress"], 9)
            self.assertEqual(reason, "progress-target-reached")

    def test_failure_marker_precedes_success_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            _, state = relay_state(directory)
            success = Path(directory) / "success"
            failure = Path(directory) / "failed"
            success.touch()
            failure.touch()
            state["monitor"]["success_markers"] = [str(success)]
            state["monitor"]["failure_markers"] = [str(failure)]
            observation, reason = MODULE.observe(state)
            self.assertEqual(reason, "failure-marker")
            self.assertEqual(observation["failure_markers"], [str(failure)])

    def test_fatal_pattern_precedes_success_log_pattern(self):
        with tempfile.TemporaryDirectory() as directory:
            _, state = relay_state(directory)
            Path(state["monitor"]["log_path"]).write_text(
                "SUCCESS\nTraceback (most recent call last):\nboom\n", encoding="utf-8"
            )
            state["monitor"]["success_patterns"] = ["SUCCESS"]
            state["monitor"]["fatal_patterns"] = [r"Traceback \(most recent call last\):"]
            observation, reason = MODULE.observe(state)
            self.assertEqual(reason, "fatal-log-pattern")
            self.assertIn("Traceback", observation["fatal_excerpt"])

    def test_event_id_is_stable_within_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            _, state = relay_state(directory)
            observation = {"progress": 10}
            first = MODULE.make_event(state, "progress-target-reached", observation)
            second = MODULE.make_event(state, "progress-target-reached", observation)
            self.assertEqual(first["id"], second["id"])
            state["generation"] = 2
            third = MODULE.make_event(state, "progress-target-reached", observation)
            self.assertNotEqual(first["id"], third["id"])


class RelayDeliveryTests(unittest.TestCase):
    def test_command_delivery_persists_attempt_before_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path, state = relay_state(directory)
            state["delivery"] = {
                "mode": "codex-resume",
                "codex_path": "/fake/codex",
                "thread_id": "thread-1",
                "session_path": None,
                "max_wake_attempts": 3,
            }
            state["pending_event"] = MODULE.make_event(state, "manual-test", {})
            MODULE.atomic_write_json(state_path, state)

            def inspect_state(*args, **kwargs):
                persisted = MODULE.load_state(state_path)
                self.assertEqual(persisted["pending_event"]["attempts"], 1)
                self.assertEqual(persisted["pending_event"]["delivery"], "in-flight")
                return mock.Mock(returncode=0, stdout="resumed")

            with mock.patch.object(MODULE.subprocess, "run", side_effect=inspect_state) as run:
                self.assertTrue(MODULE.deliver(state, state_path))
            self.assertEqual(
                run.call_args.args[0],
                ["/fake/codex", "exec", "resume", "thread-1", "-"],
            )
            self.assertIn("Long-task relay event", run.call_args.kwargs["input"])

    def test_inbox_delivery_contains_compact_context(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path, state = relay_state(directory)
            state["context_paths"] = [str(Path(directory) / "track.md")]
            state["pending_event"] = MODULE.make_event(
                state,
                "fatal-log-pattern",
                {"fatal_excerpt": "short failure", "log_size": 10_000_000},
            )
            MODULE.atomic_write_json(state_path, state)
            self.assertTrue(MODULE.deliver(state, state_path))
            prompt = Path(state["delivery"]["inbox_path"]).read_text(encoding="utf-8")
            self.assertIn("short failure", prompt)
            self.assertIn("track.md", prompt)
            self.assertNotIn("10000000", prompt)

    def test_thread_idle_requires_complete_and_quiet_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            _, state = relay_state(directory)
            transcript = Path(directory) / "session.jsonl"
            transcript.write_text(
                json.dumps(
                    {
                        "type": "event_msg",
                        "payload": {"type": "task_complete", "turn_id": "turn-1"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            old = time.time() - 30
            os.utime(transcript, (old, old))
            state["delivery"]["session_path"] = str(transcript)
            state["delivery"]["thread_quiet_seconds"] = 15
            observation = MODULE.thread_idle_observation(state)
            self.assertTrue(observation["idle"])
            self.assertEqual(observation["latest_turn_id"], "turn-1")

    def test_tui_pane_info_reads_exact_identity(self):
        completed = mock.Mock(returncode=0, stdout="%9\t42360\tcodex\n")
        with mock.patch.object(MODULE.subprocess, "run", return_value=completed) as run:
            self.assertEqual(
                MODULE.tui_pane_info("%9"),
                {"pane_id": "%9", "pane_pid": 42360, "command": "codex"},
            )
        self.assertEqual(run.call_args.args[0][0:3], ["tmux", "display-message", "-pt"])


class RelayLifecycleTests(unittest.TestCase):
    def test_background_watcher_establishes_heartbeat_and_cancels(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path, state = relay_state(directory)
            Path(state["monitor"]["log_path"]).write_text("working\n", encoding="utf-8")
            MODULE.atomic_write_json(state_path, state)
            pid = MODULE.start_background(state_path)
            try:
                status = MODULE.status_payload(state_path)
                self.assertEqual(status["status"], "watching")
                self.assertEqual(status["watcher_pid"], pid)
                self.assertTrue(status["watcher_alive"])
                args = mock.Mock(state=str(state_path))
                MODULE.command_cancel(args)
                deadline = time.monotonic() + 4
                while time.monotonic() < deadline and MODULE.process_alive(pid):
                    time.sleep(0.05)
                self.assertFalse(MODULE.process_alive(pid))
                self.assertEqual(MODULE.load_state(state_path)["status"], "cancelled")
            finally:
                if MODULE.process_alive(pid):
                    os.kill(pid, 15)

    def test_background_watcher_accepts_immediate_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path, state = relay_state(directory)
            Path(state["monitor"]["log_path"]).write_text("step=10\n", encoding="utf-8")
            state["monitor"]["progress"] = {
                "source": "log",
                "regex": r"step=(\d+)",
                "target": 10,
            }
            MODULE.atomic_write_json(state_path, state)
            pid = MODULE.start_background(state_path)
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and MODULE.process_alive(pid):
                time.sleep(0.05)
            completed = MODULE.load_state(state_path)
            self.assertEqual(completed["status"], "notified")
            self.assertEqual(completed["pending_event"]["reason"], "progress-target-reached")
            self.assertTrue(Path(completed["delivery"]["inbox_path"]).exists())


if __name__ == "__main__":
    unittest.main()
