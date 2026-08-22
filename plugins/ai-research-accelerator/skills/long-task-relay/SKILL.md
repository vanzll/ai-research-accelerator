---
name: long-task-relay
description: Monitor long-running commands with a token-free rule-based watcher that wakes the exact agent conversation only for milestones, failures, stalls, or completion. Use when an agent would otherwise sleep and poll a task for minutes or hours.
---

# Long-Task Relay

Use a mechanical watcher for waiting and an agent only for judgment. The agent
arms the watcher, verifies it, and ends the current turn. The watcher polls
local state without calling a model, then delivers one compact event to the
same conversation when attention is required.

Do not keep an agent alive to run `sleep`/status loops. Do not let the watcher
interpret results, edit files, or choose a new task.

## Choose the Mode

- Use a deterministic supervisor when every transition and recovery action is
  already authorized. It should complete the workflow without waking an agent.
- Use this relay when completion, failure, a milestone, or a stale heartbeat
  requires diagnosis or a research decision.
- Use ordinary foreground execution when the task is expected to finish within
  the current bounded turn.

## Workflow

1. Identify a durable state path, preferably on persistent storage.
2. Define observable triggers: progress target, success/failure marker, fatal
   log pattern, process/tmux exit, or stale log.
3. Select a delivery adapter:
   - `codex-resume` resumes the exact Codex thread;
   - `command` invokes an explicit resume command with the prompt on stdin;
   - `tui-send-keys` injects into a verified Codex/agent tmux pane;
   - `inbox` writes the event prompt without invoking a model.
4. Arm the watcher with
   [scripts/long_task_relay.py](scripts/long_task_relay.py), verify its state
   and heartbeat, then end the agent turn.
5. When woken, inspect primary evidence, handle exactly one event, acknowledge
   it, and re-arm with a new generation only if more waiting is needed.

Read [references/relay-protocol.md](references/relay-protocol.md) before
constructing a production relay or a remote-agent prompt.

## Safety Contract

- Persist state atomically and deduplicate events before invoking an agent.
- Wait for the target conversation to be idle before delivery when a transcript
  is available.
- Verify an interactive pane's command and PID before injecting text.
- Bound wake attempts and use backoff. A failed wake must become durable state,
  not an infinite token-consuming retry loop.
- Send only the event reason, progress, compact evidence, identities, and paths.
  Never paste an entire log or W&B history into the wake prompt.
- Treat state files as trusted executable configuration. In particular,
  `command` delivery may execute the configured argv without a shell.
- A watcher observes and notifies. Automatic restart or mutation belongs in a
  separately reviewed deterministic supervisor.

## Minimal Example

```bash
python "$RELAY" arm \
  --state /persistent/task.relay.json \
  --name long-evaluation \
  --log /persistent/task.log \
  --pid "$TASK_PID" \
  --progress-regex 'step[=: ]+(\d+)' \
  --target 1000 \
  --fatal-pattern 'Traceback|CUDA out of memory' \
  --delivery-mode codex-resume \
  --thread-id "$CODEX_THREAD_ID" \
  --session-path "$CODEX_SESSION_PATH" \
  --background
```

After arming, run `status --state ...` once to verify `watcher_pid`,
`status=watching`, and the monitored identities. Do not continue polling from
the agent session.
