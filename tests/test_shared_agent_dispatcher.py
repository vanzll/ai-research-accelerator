from __future__ import annotations

import argparse
import importlib.util
import json
import os
import tempfile
import threading
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
    / "shared_agent_dispatcher.py"
)
SPEC = importlib.util.spec_from_file_location("shared_agent_dispatcher", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def initialize(root: Path) -> dict:
    args = argparse.Namespace(
        root=str(root),
        authority_root=str(root.parent / f"{root.name}-authority"),
        experiment_id="EXP-1",
        attempt="A2",
        launch_nonce="nonce-a2",
        science_contract_hash="a" * 64,
        fencing_epoch=2,
        coordinator_node="node0",
        coordinator_thread_id="test-coordinator-thread",
        node=[("node0", MODULE.short_hostname()), ("node1", "worker-one")],
        allow_host_mismatch=False,
    )
    MODULE.initialize_bus(args)
    return MODULE.load_manifest(root)


def publish(root: Path, message: str, request_id: str) -> Path:
    args = argparse.Namespace(
        root=str(root),
        target="node1",
        action="node-local-recovery",
        message=message,
        message_file=None,
        completion_predicate="write bounded evidence and return",
        evidence_path=[str(root / "evidence.log")],
        request_id=request_id,
    )
    with mock.patch.dict(os.environ, {"CODEX_THREAD_ID": "test-coordinator-thread"}):
        MODULE.publish_request(args)
    return next((root / "inbox" / "node1").glob(f"*{request_id}.json"))


def wait_until(predicate, timeout: float = 10) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError("condition did not become true before timeout")


def initialize_campaign_fixture(base: Path) -> dict:
    base = base.resolve()
    authority = base / "authority"
    attempts = base / "attempts"
    campaign_root = base / "campaign"
    common = {
        "authority_root": str(authority),
        "experiment_id": "EXP-1",
        "science_contract_hash": "a" * 64,
        "coordinator_node": "node0",
        "coordinator_thread_id": "test-coordinator-thread",
        "node": [
            ("node0", MODULE.short_hostname()),
            ("node1", MODULE.short_hostname()),
        ],
        "allow_host_mismatch": False,
    }
    with mock.patch.dict(os.environ, {"CODEX_THREAD_ID": "test-coordinator-thread"}):
        MODULE.initialize_campaign(
            argparse.Namespace(
                root=str(campaign_root),
                authority_root=str(authority),
                attempts_root=str(attempts),
                campaign_id="CAMPAIGN-1",
                science_contract_hash="a" * 64,
                coordinator_node="node0",
                coordinator_thread_id="test-coordinator-thread",
                node=common["node"],
                allow_host_mismatch=False,
            )
        )
    attempt = attempts / "A2"
    MODULE.initialize_bus(
        argparse.Namespace(
            root=str(attempt),
            attempt="A2",
            launch_nonce="nonce-a2",
            fencing_epoch=2,
            **common,
        )
    )
    with mock.patch.dict(os.environ, {"CODEX_THREAD_ID": "test-coordinator-thread"}):
        MODULE.activate_campaign_attempt(
            argparse.Namespace(
                root=str(campaign_root),
                attempt_root=str(attempt),
                expected_previous_epoch=-1,
            )
        )
    return {
        "authority": authority,
        "attempts": attempts,
        "campaign": campaign_root,
        "attempt": attempt,
        "common": common,
    }


def make_idle_transcript(root: Path) -> Path:
    path = root / "session.jsonl"
    path.write_text(
        json.dumps(
            {
                "type": "event_msg",
                "payload": {"type": "task_complete", "turn_id": "bootstrap"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    old = time.time() - 30
    os.utime(path, (old, old))
    return path


def make_fake_codex(root: Path) -> Path:
    path = root / "fake-codex"
    path.write_text(
        """#!/usr/bin/env python3
import json
import pathlib
import sys

args = sys.argv[1:]
output = pathlib.Path(args[args.index('--output-last-message') + 1])
prompt = sys.stdin.read()
request = next(line for line in prompt.splitlines() if line.startswith('Request: ')).split(': ', 1)[1]
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({'status': 'succeeded', 'summary': 'handled ' + request, 'evidence_paths': []}))
with (output.parent / 'invocations.log').open('a') as handle:
    handle.write(request + '\\n')
""",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def make_slow_fake_codex(root: Path) -> Path:
    path = root / "slow-fake-codex"
    path.write_text(
        """#!/usr/bin/env python3
import time
time.sleep(60)
""",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def make_releasable_fake_codex(root: Path) -> Path:
    path = root / "releasable-fake-codex"
    path.write_text(
        """#!/usr/bin/env python3
import json
import pathlib
import sys
import time

args = sys.argv[1:]
output = pathlib.Path(args[args.index('--output-last-message') + 1])
root = output.parents[3]
prompt = sys.stdin.read()
request = next(line for line in prompt.splitlines() if line.startswith('Request: ')).split(': ', 1)[1]
(root / ('entered-' + request)).write_text('entered')
while not (root / ('release-' + request)).exists():
    time.sleep(0.05)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({'status': 'succeeded', 'summary': 'handled ' + request, 'evidence_paths': []}))
with (output.parent / 'invocations.log').open('a') as handle:
    handle.write(request + '\\n')
""",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


class SharedAgentDispatcherTests(unittest.TestCase):
    def campaign_start_args(self, fixture: dict, codex_path: Path) -> argparse.Namespace:
        campaign = fixture["campaign"]
        return argparse.Namespace(
            root=str(campaign),
            node="node1",
            thread_id="thread-1",
            session_path=str(make_idle_transcript(campaign)),
            workdir=str(campaign),
            codex_path=str(codex_path),
            poll_interval=0.1,
            task_timeout=30,
            thread_quiet_seconds=1,
            thread_idle_timeout=30,
            restart_backoff=0.1,
        )

    def test_process_matching_honors_omitted_default_instance_id(self):
        root = Path("/tmp/campaign-default-instance").resolve()
        state = {
            "pid": os.getpid(),
            "process_start_token": MODULE.process_start_token(os.getpid()),
            "instance_id": MODULE.DEFAULT_INSTANCE_ID,
        }
        common = [
            "python3",
            str(SCRIPT),
            "--root",
            str(root),
            "--node",
            "node1",
        ]

        with mock.patch.object(
            MODULE,
            "process_argv",
            return_value=[common[0], common[1], "campaign-run", *common[2:]],
        ):
            self.assertTrue(MODULE.dispatcher_process_matches(state, root, "node1"))

        with mock.patch.object(
            MODULE,
            "process_argv",
            return_value=[
                common[0],
                common[1],
                "campaign-supervise",
                *common[2:],
            ],
        ):
            self.assertTrue(
                MODULE.campaign_supervisor_process_matches(state, root, "node1")
            )

    def test_campaign_dispatcher_survives_attempt_transition_and_only_goal_completes(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = initialize_campaign_fixture(Path(directory))
            campaign = fixture["campaign"]
            first = fixture["attempt"]
            args = self.campaign_start_args(fixture, make_fake_codex(campaign))
            MODULE.start_campaign_dispatcher(args)
            supervisor_path = MODULE.campaign_supervisor_state_path(campaign, "node1")
            state_path = MODULE.dispatcher_state_path(campaign, "node1")
            supervisor_pid = MODULE.read_json(supervisor_path)["pid"]
            dispatcher_pid = MODULE.read_json(state_path)["pid"]

            publish(first, "handle A2", "campaign-a2")
            wait_until(lambda: (first / "results" / "node1" / "campaign-a2.json").exists())
            with mock.patch.dict(
                os.environ, {"CODEX_THREAD_ID": "test-coordinator-thread"}
            ):
                MODULE.close_bus(
                    argparse.Namespace(
                        root=str(first), status="abandoned", summary="retry A3"
                    )
                )
            wait_until(
                lambda: MODULE.read_json(state_path).get("active_attempt_terminal")
                is True
            )
            self.assertEqual(MODULE.read_json(supervisor_path)["pid"], supervisor_pid)
            self.assertEqual(MODULE.read_json(state_path)["pid"], dispatcher_pid)

            second = fixture["attempts"] / "A3"
            MODULE.initialize_bus(
                argparse.Namespace(
                    root=str(second),
                    attempt="A3",
                    launch_nonce="nonce-a3",
                    fencing_epoch=3,
                    **fixture["common"],
                )
            )
            with mock.patch.dict(
                os.environ, {"CODEX_THREAD_ID": "test-coordinator-thread"}
            ):
                MODULE.activate_campaign_attempt(
                    argparse.Namespace(
                        root=str(campaign),
                        attempt_root=str(second),
                        expected_previous_epoch=2,
                    )
                )
            wait_until(
                lambda: MODULE.read_json(state_path).get("active_attempt") == "A3"
            )
            self.assertEqual(MODULE.read_json(supervisor_path)["pid"], supervisor_pid)
            self.assertEqual(MODULE.read_json(state_path)["pid"], dispatcher_pid)
            publish(second, "handle A3", "campaign-a3")
            wait_until(lambda: (second / "results" / "node1" / "campaign-a3.json").exists())

            with mock.patch.dict(
                os.environ, {"CODEX_THREAD_ID": "test-coordinator-thread"}
            ):
                MODULE.complete_campaign(
                    argparse.Namespace(
                        root=str(campaign),
                        expected_attempt_root=str(second),
                        expected_attempt="A3",
                        expected_launch_nonce="nonce-a3",
                        expected_fencing_epoch=3,
                        summary="Goal achieved",
                        evidence_path=[str(second / "results")],
                    )
                )
            wait_until(
                lambda: MODULE.read_json(state_path).get("status") == "goal-completed"
            )
            wait_until(lambda: not MODULE.process_alive(supervisor_pid))
            with self.assertRaisesRegex(ValueError, "already completed"):
                MODULE.start_campaign_dispatcher(args)
            with self.assertRaisesRegex(ValueError, "already completed"):
                publish(second, "must not run", "after-goal")

    def test_campaign_dispatcher_waits_through_invalid_active_pointer(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = initialize_campaign_fixture(Path(directory))
            campaign = fixture["campaign"]
            args = self.campaign_start_args(fixture, make_fake_codex(campaign))
            MODULE.start_campaign_dispatcher(args)
            state_path = MODULE.dispatcher_state_path(campaign, "node1")
            dispatcher_pid = MODULE.read_json(state_path)["pid"]
            active_path = MODULE.campaign_active_attempt_path(campaign)
            valid = MODULE.read_json(active_path)
            invalid = {**valid, "root": str(fixture["attempts"] / "missing")}
            MODULE.atomic_replace_json(active_path, invalid)
            wait_until(
                lambda: MODULE.read_json(state_path).get("status")
                == "waiting-for-active-attempt"
            )
            self.assertTrue(MODULE.process_alive(dispatcher_pid))
            MODULE.atomic_replace_json(active_path, valid)
            wait_until(
                lambda: MODULE.read_json(state_path).get("status") == "watching"
            )
            self.assertEqual(MODULE.read_json(state_path)["pid"], dispatcher_pid)
            MODULE.stop_campaign_dispatcher(
                argparse.Namespace(root=str(campaign), node="node1", timeout=5)
            )

    def test_campaign_supervisor_restarts_crashed_dispatcher(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = initialize_campaign_fixture(Path(directory))
            campaign = fixture["campaign"]
            args = self.campaign_start_args(fixture, make_fake_codex(campaign))
            MODULE.start_campaign_dispatcher(args)
            supervisor_path = MODULE.campaign_supervisor_state_path(campaign, "node1")
            state_path = MODULE.dispatcher_state_path(campaign, "node1")
            supervisor_pid = MODULE.read_json(supervisor_path)["pid"]
            first_dispatcher_pid = MODULE.read_json(state_path)["pid"]
            os.kill(first_dispatcher_pid, 9)
            wait_until(
                lambda: MODULE.read_json(state_path).get("pid")
                not in {None, first_dispatcher_pid}
                and MODULE.dispatcher_process_matches(
                    MODULE.read_json(state_path), campaign, "node1"
                )
            )
            self.assertEqual(MODULE.read_json(supervisor_path)["pid"], supervisor_pid)
            self.assertGreaterEqual(
                int(MODULE.read_json(supervisor_path).get("restart_count", 0)), 1
            )
            MODULE.stop_campaign_dispatcher(
                argparse.Namespace(root=str(campaign), node="node1", timeout=5)
            )

    def test_campaign_compare_and_swap_rejects_stale_close_and_activation(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = initialize_campaign_fixture(Path(directory))
            campaign = fixture["campaign"]
            second = fixture["attempts"] / "A3"
            MODULE.initialize_bus(
                argparse.Namespace(
                    root=str(second),
                    attempt="A3",
                    launch_nonce="nonce-a3",
                    fencing_epoch=3,
                    **fixture["common"],
                )
            )
            with mock.patch.dict(
                os.environ, {"CODEX_THREAD_ID": "test-coordinator-thread"}
            ):
                with self.assertRaisesRegex(ValueError, "compare-and-swap"):
                    MODULE.activate_campaign_attempt(
                        argparse.Namespace(
                            root=str(campaign),
                            attempt_root=str(second),
                            expected_previous_epoch=1,
                        )
                    )
                MODULE.activate_campaign_attempt(
                    argparse.Namespace(
                        root=str(campaign),
                        attempt_root=str(second),
                        expected_previous_epoch=2,
                    )
                )
                with self.assertRaisesRegex(ValueError, "compare-and-swap"):
                    MODULE.complete_campaign(
                        argparse.Namespace(
                            root=str(campaign),
                            expected_attempt_root=str(fixture["attempt"]),
                            expected_attempt="A2",
                            expected_launch_nonce="nonce-a2",
                            expected_fencing_epoch=2,
                            summary="stale close",
                            evidence_path=[],
                        )
                    )
            self.assertFalse(MODULE.campaign_goal_completed_path(campaign).exists())

    def test_campaign_completion_drains_active_turn_and_never_starts_queued_work(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = initialize_campaign_fixture(Path(directory))
            campaign = fixture["campaign"]
            attempt = fixture["attempt"]
            MODULE.start_campaign_dispatcher(
                self.campaign_start_args(
                    fixture, make_releasable_fake_codex(attempt)
                )
            )
            supervisor_pid = MODULE.read_json(
                MODULE.campaign_supervisor_state_path(campaign, "node1")
            )["pid"]
            publish(attempt, "finish active work", "campaign-active")
            publish(attempt, "must remain queued", "campaign-queued")
            wait_until(lambda: (attempt / "entered-campaign-active").exists())
            errors = []

            def complete():
                try:
                    with mock.patch.dict(
                        os.environ,
                        {"CODEX_THREAD_ID": "test-coordinator-thread"},
                    ):
                        MODULE.complete_campaign(
                            argparse.Namespace(
                                root=str(campaign),
                                expected_attempt_root=str(attempt),
                                expected_attempt="A2",
                                expected_launch_nonce="nonce-a2",
                                expected_fencing_epoch=2,
                                summary="active request drained",
                                evidence_path=[],
                            )
                        )
                except Exception as error:  # pragma: no cover - surfaced below
                    errors.append(error)

            thread = threading.Thread(target=complete)
            thread.start()
            time.sleep(0.3)
            self.assertTrue(thread.is_alive(), "completion must drain the active Agent turn")
            (attempt / "release-campaign-active").write_text(
                "release", encoding="utf-8"
            )
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            wait_until(
                lambda: MODULE.read_json(
                    MODULE.dispatcher_state_path(campaign, "node1")
                ).get("status")
                == "goal-completed"
            )
            self.assertFalse((attempt / "entered-campaign-queued").exists())
            invocation_log = (
                attempt
                / "dispatcher"
                / "node1"
                / "agent-results"
                / "invocations.log"
            )
            self.assertEqual(invocation_log.read_text().splitlines(), ["campaign-active"])
            wait_until(lambda: not MODULE.process_alive(supervisor_pid))

    def test_background_worker_waits_for_manifest_then_watches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transcript = make_idle_transcript(root)
            fake_codex = make_fake_codex(root)
            start_args = argparse.Namespace(
                root=str(root),
                authority_root=str(root.parent / f"{root.name}-authority"),
                node="node1",
                thread_id="thread-1",
                session_path=str(transcript),
                workdir=str(root),
                codex_path=str(fake_codex),
                poll_interval=0.1,
                task_timeout=30,
                thread_quiet_seconds=1,
                thread_idle_timeout=30,
            )
            MODULE.start_dispatcher(start_args)
            state_path = MODULE.dispatcher_state_path(root, "node1")
            self.assertEqual(MODULE.read_json(state_path)["status"], "waiting-for-manifest")
            init_args = argparse.Namespace(
                root=str(root),
                authority_root=str(root.parent / f"{root.name}-authority"),
                experiment_id="EXP-1",
                attempt="A2",
                launch_nonce="nonce-a2",
                science_contract_hash="a" * 64,
                fencing_epoch=2,
                coordinator_node="node0",
                coordinator_thread_id="test-coordinator-thread",
                node=[
                    ("node0", MODULE.short_hostname()),
                    ("node1", MODULE.short_hostname()),
                ],
                allow_host_mismatch=False,
            )
            MODULE.initialize_bus(init_args)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if MODULE.read_json(state_path)["status"] == "watching":
                    break
                time.sleep(0.1)
            self.assertEqual(MODULE.read_json(state_path)["status"], "watching")
            MODULE.stop_dispatcher(
                argparse.Namespace(root=str(root), node="node1", timeout=5)
            )

    def test_manifest_is_immutable_and_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize(root)
            initialize(root)
            args = argparse.Namespace(
                root=str(root),
                authority_root=str(root.parent / f"{root.name}-authority"),
                experiment_id="EXP-1",
                attempt="A3",
                launch_nonce="nonce-a3",
                science_contract_hash="a" * 64,
                fencing_epoch=3,
                coordinator_node="node0",
                coordinator_thread_id="test-coordinator-thread",
                node=[("node0", MODULE.short_hostname()), ("node1", "worker-one")],
                allow_host_mismatch=False,
            )
            with self.assertRaisesRegex(ValueError, "mismatched manifest"):
                MODULE.initialize_bus(args)

    def test_new_epoch_supersedes_old_bus(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            authority = base / "authority"
            first = base / "attempt-a2"
            second = base / "attempt-a3"
            common = {
                "authority_root": str(authority),
                "experiment_id": "EXP-1",
                "science_contract_hash": "a" * 64,
                "coordinator_node": "node0",
                "coordinator_thread_id": "test-coordinator-thread",
                "node": [
                    ("node0", MODULE.short_hostname()),
                    ("node1", "worker-one"),
                ],
                "allow_host_mismatch": False,
            }
            MODULE.initialize_bus(
                argparse.Namespace(
                    root=str(first),
                    attempt="A2",
                    launch_nonce="nonce-a2",
                    fencing_epoch=2,
                    **common,
                )
            )
            MODULE.initialize_bus(
                argparse.Namespace(
                    root=str(second),
                    attempt="A3",
                    launch_nonce="nonce-a3",
                    fencing_epoch=3,
                    **common,
                )
            )
            with self.assertRaisesRegex(ValueError, "superseded"):
                MODULE.validate_active_authority(first, MODULE.load_manifest(first))
            with mock.patch.dict(
                os.environ, {"CODEX_THREAD_ID": "test-coordinator-thread"}
            ):
                with self.assertRaisesRegex(ValueError, "superseded"):
                    MODULE.publish_request(
                        argparse.Namespace(
                            root=str(first),
                            target="node1",
                            action="stale",
                            message="must not run",
                            message_file=None,
                            completion_predicate="none",
                            evidence_path=[],
                            request_id="stale-after-supersede",
                        )
                    )

    def test_supersede_before_gate_prevents_codex_spawn(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            authority = base / "authority"
            first = base / "attempt-a2"
            second = base / "attempt-a3"
            common = {
                "authority_root": str(authority),
                "experiment_id": "EXP-1",
                "science_contract_hash": "a" * 64,
                "coordinator_node": "node0",
                "coordinator_thread_id": "test-coordinator-thread",
                "node": [
                    ("node0", MODULE.short_hostname()),
                    ("node1", "worker-one"),
                ],
                "allow_host_mismatch": False,
            }
            MODULE.initialize_bus(
                argparse.Namespace(
                    root=str(first),
                    attempt="A2",
                    launch_nonce="nonce-a2",
                    fencing_epoch=2,
                    **common,
                )
            )
            manifest = MODULE.load_manifest(first)
            publish(first, "queued old request", "queued-a2")

            def supersede_then_idle(*_args):
                MODULE.initialize_bus(
                    argparse.Namespace(
                        root=str(second),
                        attempt="A3",
                        launch_nonce="nonce-a3",
                        fencing_epoch=3,
                        **common,
                    )
                )
                return True

            fake_codex = make_fake_codex(first)
            with mock.patch.object(MODULE, "thread_idle", side_effect=supersede_then_idle):
                MODULE.dispatch_pending_once(
                    first,
                    manifest,
                    "node1",
                    "thread-1",
                    make_idle_transcript(first),
                    str(fake_codex),
                    first,
                    30,
                    1,
                    30,
                )
            result = MODULE.read_json(first / "results" / "node1" / "queued-a2.json")
            self.assertEqual(result["status"], "needs_coordinator")
            self.assertFalse(
                (first / "dispatcher" / "node1" / "agent-results" / "invocations.log").exists()
            )

    def test_rejected_lower_epoch_does_not_publish_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            authority = base / "authority"
            first = base / "attempt-a2"
            invalid = base / "invalid-a3"
            common = {
                "authority_root": str(authority),
                "experiment_id": "EXP-1",
                "science_contract_hash": "a" * 64,
                "coordinator_node": "node0",
                "coordinator_thread_id": "test-coordinator-thread",
                "node": [
                    ("node0", MODULE.short_hostname()),
                    ("node1", "worker-one"),
                ],
                "allow_host_mismatch": False,
            }
            MODULE.initialize_bus(
                argparse.Namespace(
                    root=str(first),
                    attempt="A2",
                    launch_nonce="nonce-a2",
                    fencing_epoch=2,
                    **common,
                )
            )
            with self.assertRaisesRegex(ValueError, "strictly greater"):
                MODULE.initialize_bus(
                    argparse.Namespace(
                        root=str(invalid),
                        attempt="A3",
                        launch_nonce="invalid",
                        fencing_epoch=1,
                        **common,
                    )
                )
            self.assertFalse(MODULE.manifest_path(invalid).exists())

    def test_dispatcher_processes_repeated_requests_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = initialize(root)
            publish(root, "perform first bounded task", "request-one")
            publish(root, "perform second bounded task", "request-two")
            transcript = make_idle_transcript(root)
            fake_codex = make_fake_codex(root)
            MODULE.dispatch_pending_once(
                root,
                manifest,
                "node1",
                "thread-1",
                transcript,
                str(fake_codex),
                root,
                30,
                1,
                30,
            )
            results = sorted((root / "results" / "node1").glob("*.json"))
            self.assertEqual(len(results), 2)
            self.assertEqual(
                {json.loads(path.read_text())["status"] for path in results},
                {"succeeded"},
            )
            self.assertEqual(len(list((root / "acks" / "node1").glob("*.json"))), 2)
            invocation_log = (
                root / "dispatcher" / "node1" / "agent-results" / "invocations.log"
            )
            self.assertEqual(invocation_log.read_text().splitlines(), ["request-one", "request-two"])

            MODULE.dispatch_pending_once(
                root,
                manifest,
                "node1",
                "thread-1",
                transcript,
                str(fake_codex),
                root,
                30,
                1,
                30,
            )
            self.assertEqual(invocation_log.read_text().splitlines(), ["request-one", "request-two"])

    def test_stale_request_is_rejected_without_agent_invocation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = initialize(root)
            request_path = publish(root, "do not run stale work", "stale-request")
            request = MODULE.read_json(request_path)
            request["fencing_epoch"] = 1
            MODULE.atomic_replace_json(request_path, request)
            transcript = make_idle_transcript(root)
            fake_codex = make_fake_codex(root)
            MODULE.dispatch_pending_once(
                root,
                manifest,
                "node1",
                "thread-1",
                transcript,
                str(fake_codex),
                root,
                30,
                1,
                30,
            )
            result = MODULE.read_json(root / "results" / "node1" / "stale-request.json")
            ack = MODULE.read_json(root / "acks" / "node1" / "stale-request.json")
            self.assertEqual(result["status"], "failed")
            self.assertEqual(ack["status"], "rejected")
            self.assertFalse(
                (root / "dispatcher" / "node1" / "agent-results" / "invocations.log").exists()
            )

    def test_expired_pre_delivery_claim_is_safely_reclaimed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = initialize(root)
            request_path = publish(root, "recover claim", "reclaim-request")
            request = MODULE.read_json(request_path)
            MODULE.atomic_create_json(
                root / "claims" / "node1" / "reclaim-request.json",
                MODULE.worker_record(
                    manifest,
                    "node1",
                    request,
                    status="claimed",
                    lease_expires_unix=time.time() - 1,
                ),
            )
            MODULE.dispatch_pending_once(
                root,
                manifest,
                "node1",
                "thread-1",
                make_idle_transcript(root),
                str(make_fake_codex(root)),
                root,
                30,
                1,
                30,
            )
            result = MODULE.read_json(root / "results" / "node1" / "reclaim-request.json")
            self.assertEqual(result["status"], "succeeded")

    def test_thread_idle_wait_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = initialize(root)
            publish(root, "wait for idle", "busy-thread")
            transcript = root / "busy.jsonl"
            transcript.write_text(
                json.dumps(
                    {
                        "type": "event_msg",
                        "payload": {"type": "task_started", "turn_id": "busy"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            old = time.time() - 30
            os.utime(transcript, (old, old))
            MODULE.dispatch_pending_once(
                root,
                manifest,
                "node1",
                "thread-1",
                transcript,
                str(make_fake_codex(root)),
                root,
                30,
                1,
                1,
            )
            result = MODULE.read_json(root / "results" / "node1" / "busy-thread.json")
            self.assertEqual(result["status"], "needs_coordinator")
            self.assertFalse((root / "invocations" / "node1" / "busy-thread.json").exists())

    def test_start_rejects_different_thread_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transcript = make_idle_transcript(root)
            fake_codex = make_fake_codex(root)
            args = argparse.Namespace(
                root=str(root),
                node="node1",
                thread_id="thread-1",
                session_path=str(transcript),
                workdir=str(root),
                codex_path=str(fake_codex),
                poll_interval=0.1,
                task_timeout=30,
                thread_quiet_seconds=1,
                thread_idle_timeout=30,
            )
            MODULE.start_dispatcher(args)
            changed = argparse.Namespace(**vars(args))
            changed.thread_id = "thread-2"
            with self.assertRaisesRegex(ValueError, "different configuration"):
                MODULE.start_dispatcher(changed)
            MODULE.stop_dispatcher(
                argparse.Namespace(root=str(root), node="node1", timeout=5)
            )

    def test_stop_terminates_active_agent_process_group(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transcript = make_idle_transcript(root)
            slow_codex = make_slow_fake_codex(root)
            start_args = argparse.Namespace(
                root=str(root),
                node="node1",
                thread_id="thread-1",
                session_path=str(transcript),
                workdir=str(root),
                codex_path=str(slow_codex),
                poll_interval=0.1,
                task_timeout=120,
                thread_quiet_seconds=1,
                thread_idle_timeout=30,
            )
            MODULE.start_dispatcher(start_args)
            init_args = argparse.Namespace(
                root=str(root),
                authority_root=str(root.parent / f"{root.name}-authority"),
                experiment_id="EXP-1",
                attempt="A2",
                launch_nonce="nonce-a2",
                science_contract_hash="a" * 64,
                fencing_epoch=2,
                coordinator_node="node0",
                coordinator_thread_id="test-coordinator-thread",
                node=[
                    ("node0", MODULE.short_hostname()),
                    ("node1", MODULE.short_hostname()),
                ],
                allow_host_mismatch=False,
            )
            MODULE.initialize_bus(init_args)
            publish(root, "run long node task", "long-request")
            invocation_path = root / "invocations" / "node1" / "long-request.json"
            deadline = time.monotonic() + 10
            while not invocation_path.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            self.assertTrue(invocation_path.exists())
            invocation = MODULE.read_json(invocation_path)
            started_path = Path(invocation["started_path"])
            while not started_path.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            self.assertTrue(started_path.exists())
            started = MODULE.read_json(started_path)
            MODULE.stop_dispatcher(
                argparse.Namespace(root=str(root), node="node1", timeout=10)
            )
            result = MODULE.read_json(root / "results" / "node1" / "long-request.json")
            self.assertEqual(result["status"], "needs_coordinator")
            self.assertFalse(MODULE.process_alive(int(invocation["helper_pid"])))
            self.assertFalse(MODULE.process_alive(int(started["codex_pid"])))

    def test_sigkill_helper_does_not_leave_orphan_codex(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transcript = make_idle_transcript(root)
            slow_codex = make_slow_fake_codex(root)
            start_args = argparse.Namespace(
                root=str(root),
                node="node1",
                thread_id="thread-1",
                session_path=str(transcript),
                workdir=str(root),
                codex_path=str(slow_codex),
                poll_interval=0.1,
                task_timeout=120,
                thread_quiet_seconds=1,
                thread_idle_timeout=30,
            )
            MODULE.start_dispatcher(start_args)
            MODULE.initialize_bus(
                argparse.Namespace(
                    root=str(root),
                    authority_root=str(root.parent / f"{root.name}-authority"),
                    experiment_id="EXP-1",
                    attempt="A2",
                    launch_nonce="nonce-a2",
                    science_contract_hash="a" * 64,
                    fencing_epoch=2,
                    coordinator_node="node0",
                    coordinator_thread_id="test-coordinator-thread",
                    node=[
                        ("node0", MODULE.short_hostname()),
                        ("node1", MODULE.short_hostname()),
                    ],
                    allow_host_mismatch=False,
                )
            )
            publish(root, "run long node task", "kill-helper-request")
            invocation_path = root / "invocations" / "node1" / "kill-helper-request.json"
            deadline = time.monotonic() + 10
            while not invocation_path.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            invocation = MODULE.read_json(invocation_path)
            started_path = Path(invocation["started_path"])
            while not started_path.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            started = MODULE.read_json(started_path)
            os.kill(int(invocation["helper_pid"]), 9)
            result_path = root / "results" / "node1" / "kill-helper-request.json"
            while not result_path.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            self.assertTrue(result_path.exists())
            self.assertEqual(MODULE.read_json(result_path)["status"], "needs_coordinator")
            while MODULE.process_alive(int(started["codex_pid"])) and time.monotonic() < deadline:
                time.sleep(0.1)
            self.assertFalse(MODULE.process_alive(int(started["codex_pid"])))
            MODULE.stop_dispatcher(
                argparse.Namespace(root=str(root), node="node1", timeout=10)
            )

    def test_codex_keeps_epoch_fence_after_helper_and_dispatcher_die(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "attempt-a2"
            authority = base / "authority"
            root.mkdir()
            common = {
                "authority_root": str(authority),
                "experiment_id": "EXP-1",
                "science_contract_hash": "a" * 64,
                "coordinator_node": "node0",
                "coordinator_thread_id": "test-coordinator-thread",
                "node": [
                    ("node0", MODULE.short_hostname()),
                    ("node1", MODULE.short_hostname()),
                ],
                "allow_host_mismatch": False,
            }
            MODULE.start_dispatcher(
                argparse.Namespace(
                    root=str(root),
                    node="node1",
                    thread_id="thread-1",
                    session_path=str(make_idle_transcript(root)),
                    workdir=str(root),
                    codex_path=str(make_slow_fake_codex(root)),
                    poll_interval=0.1,
                    task_timeout=120,
                    thread_quiet_seconds=1,
                    thread_idle_timeout=30,
                )
            )
            MODULE.initialize_bus(
                argparse.Namespace(
                    root=str(root),
                    attempt="A2",
                    launch_nonce="nonce-a2",
                    fencing_epoch=2,
                    **common,
                )
            )
            publish(root, "hold the inherited fence", "inherited-fence")
            invocation_path = root / "invocations" / "node1" / "inherited-fence.json"
            deadline = time.monotonic() + 10
            while not invocation_path.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            invocation = MODULE.read_json(invocation_path)
            started_path = Path(invocation["started_path"])
            while not started_path.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            started = MODULE.read_json(started_path)
            dispatcher = MODULE.read_json(MODULE.dispatcher_state_path(root, "node1"))
            os.kill(int(dispatcher["pid"]), 9)
            os.kill(int(invocation["helper_pid"]), 9)
            while MODULE.process_alive(int(dispatcher["pid"])) and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(MODULE.process_alive(int(started["codex_pid"])))

            errors = []

            def advance_epoch():
                try:
                    MODULE.initialize_bus(
                        argparse.Namespace(
                            root=str(base / "attempt-a3"),
                            attempt="A3",
                            launch_nonce="nonce-a3",
                            fencing_epoch=3,
                            **common,
                        )
                    )
                except Exception as error:  # pragma: no cover - surfaced below
                    errors.append(error)

            thread = threading.Thread(target=advance_epoch)
            thread.start()
            time.sleep(0.3)
            self.assertTrue(thread.is_alive(), "Codex itself must retain the epoch fence")
            os.killpg(int(invocation["helper_pgid"]), 15)
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            self.assertFalse(MODULE.process_alive(int(started["codex_pid"])))

    def test_epoch_takeover_waits_for_active_worker_turn(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            authority = base / "authority"
            first = base / "attempt-a2"
            second = base / "attempt-a3"
            common = {
                "authority_root": str(authority),
                "experiment_id": "EXP-1",
                "science_contract_hash": "a" * 64,
                "coordinator_node": "node0",
                "coordinator_thread_id": "test-coordinator-thread",
                "node": [
                    ("node0", MODULE.short_hostname()),
                    ("node1", MODULE.short_hostname()),
                ],
                "allow_host_mismatch": False,
            }
            MODULE.initialize_bus(
                argparse.Namespace(
                    root=str(first),
                    attempt="A2",
                    launch_nonce="nonce-a2",
                    fencing_epoch=2,
                    **common,
                )
            )
            MODULE.start_dispatcher(
                argparse.Namespace(
                    root=str(first),
                    node="node1",
                    thread_id="thread-1",
                    session_path=str(make_idle_transcript(first)),
                    workdir=str(first),
                    codex_path=str(make_releasable_fake_codex(first)),
                    poll_interval=0.1,
                    task_timeout=30,
                    thread_quiet_seconds=1,
                    thread_idle_timeout=30,
                )
            )
            publish(first, "hold active turn", "active-a2")
            deadline = time.monotonic() + 10
            while not (first / "entered-active-a2").exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue((first / "entered-active-a2").exists())

            errors = []

            def advance_epoch():
                try:
                    MODULE.initialize_bus(
                        argparse.Namespace(
                            root=str(second),
                            attempt="A3",
                            launch_nonce="nonce-a3",
                            fencing_epoch=3,
                            **common,
                        )
                    )
                except Exception as error:  # pragma: no cover - surfaced below
                    errors.append(error)

            thread = threading.Thread(target=advance_epoch)
            thread.start()
            time.sleep(0.3)
            self.assertTrue(thread.is_alive(), "epoch takeover must wait for active Codex")
            self.assertEqual(
                MODULE.read_json(authority / "active-agent-bus.json")["root"],
                str(first.resolve()),
            )
            (first / "release-active-a2").write_text("release", encoding="utf-8")
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(
                MODULE.read_json(authority / "active-agent-bus.json")["root"],
                str(second.resolve()),
            )
            MODULE.stop_dispatcher(
                argparse.Namespace(root=str(first), node="node1", timeout=10)
            )

    def test_close_waits_for_active_turn_and_prevents_queued_wake(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            MODULE.start_dispatcher(
                argparse.Namespace(
                    root=str(root),
                    node="node1",
                    thread_id="thread-1",
                    session_path=str(make_idle_transcript(root)),
                    workdir=str(root),
                    codex_path=str(make_releasable_fake_codex(root)),
                    poll_interval=0.1,
                    task_timeout=30,
                    thread_quiet_seconds=1,
                    thread_idle_timeout=30,
                )
            )
            MODULE.initialize_bus(
                argparse.Namespace(
                    root=str(root),
                    authority_root=str(root.parent / f"{root.name}-authority"),
                    experiment_id="EXP-1",
                    attempt="A2",
                    launch_nonce="nonce-a2",
                    science_contract_hash="a" * 64,
                    fencing_epoch=2,
                    coordinator_node="node0",
                    coordinator_thread_id="test-coordinator-thread",
                    node=[
                        ("node0", MODULE.short_hostname()),
                        ("node1", MODULE.short_hostname()),
                    ],
                    allow_host_mismatch=False,
                )
            )
            publish(root, "hold first turn", "first-before-close")
            publish(root, "must not wake", "queued-after-close")
            deadline = time.monotonic() + 10
            while not (root / "entered-first-before-close").exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue((root / "entered-first-before-close").exists())

            errors = []

            def close():
                try:
                    with mock.patch.dict(
                        os.environ, {"CODEX_THREAD_ID": "test-coordinator-thread"}
                    ):
                        MODULE.close_bus(
                            argparse.Namespace(
                                root=str(root),
                                status="completed",
                                summary="bounded work complete",
                            )
                        )
                except Exception as error:  # pragma: no cover - surfaced below
                    errors.append(error)

            thread = threading.Thread(target=close)
            thread.start()
            time.sleep(0.3)
            self.assertTrue(thread.is_alive(), "close must wait for active Codex")
            (root / "release-first-before-close").write_text("release", encoding="utf-8")
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            deadline = time.monotonic() + 5
            state_path = MODULE.dispatcher_state_path(root, "node1")
            while MODULE.read_json(state_path)["status"] != "stopped" and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertFalse((root / "entered-queued-after-close").exists())
            invocation_log = root / "dispatcher" / "node1" / "agent-results" / "invocations.log"
            self.assertEqual(invocation_log.read_text().splitlines(), ["first-before-close"])

    def test_stop_intent_prevents_late_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = initialize(root)
            publish(root, "must not start after stop", "late-after-stop")
            stop_path = MODULE.worker_stop_path(root, "node1")
            MODULE.atomic_replace_json(stop_path, {"instance_id": "stopped"})
            MODULE.dispatch_pending_once(
                root,
                manifest,
                "node1",
                "thread-1",
                make_idle_transcript(root),
                str(make_fake_codex(root)),
                root,
                30,
                1,
                30,
            )
            result = MODULE.read_json(root / "results" / "node1" / "late-after-stop.json")
            self.assertEqual(result["status"], "needs_coordinator")
            self.assertFalse((root / "invocations" / "node1" / "late-after-stop.json").exists())

    def test_result_parser_rejects_non_object_and_nonzero_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            path.write_text("[]", encoding="utf-8")
            self.assertEqual(
                MODULE.parse_agent_result(path, 0, "")["status"], "needs_coordinator"
            )
            path.write_text(
                json.dumps(
                    {"status": "succeeded", "summary": "bad", "evidence_paths": []}
                ),
                encoding="utf-8",
            )
            self.assertEqual(MODULE.parse_agent_result(path, 1, "")["status"], "failed")

    def test_coordinator_cannot_publish_to_itself(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize(root)
            args = argparse.Namespace(
                root=str(root),
                target="node0",
                action="bad",
                message="duplicate coordinator ownership",
                message_file=None,
                completion_predicate="none",
                evidence_path=[],
                request_id="bad-request",
            )
            with self.assertRaisesRegex(ValueError, "handle its own node"):
                with mock.patch.dict(
                    os.environ, {"CODEX_THREAD_ID": "test-coordinator-thread"}
                ):
                    MODULE.publish_request(args)

    def test_only_coordinator_closes_bus_with_immutable_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize(root)
            args = argparse.Namespace(
                root=str(root), status="completed", summary="first work validated"
            )
            with mock.patch.dict(
                os.environ, {"CODEX_THREAD_ID": "test-coordinator-thread"}
            ):
                MODULE.close_bus(args)
                MODULE.close_bus(args)
            terminal = MODULE.read_json(root / "terminal.json")
            self.assertEqual(terminal["status"], "completed")
            changed = argparse.Namespace(
                root=str(root), status="abandoned", summary="different terminal"
            )
            with self.assertRaisesRegex(ValueError, "mismatched terminal"):
                with mock.patch.dict(
                    os.environ, {"CODEX_THREAD_ID": "test-coordinator-thread"}
                ):
                    MODULE.close_bus(changed)


if __name__ == "__main__":
    unittest.main()
