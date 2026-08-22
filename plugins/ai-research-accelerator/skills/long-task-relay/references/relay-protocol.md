# Long-Task Relay Protocol

## Architecture

```text
agent bootstrap
    -> trusted relay state
    -> token-free watcher process
    -> local observations
    -> one persisted event
    -> exact conversation resume or verified TUI injection
    -> agent judgment
    -> acknowledge and optionally re-arm
```

The watcher is deliberately less capable than the agent. It detects declared
conditions and packages evidence; it does not infer causes or choose actions.

## State and Event Lifecycle

The CLI writes a versioned JSON state file. Important states are:

- `armed`: configuration is durable but no watcher has claimed it yet;
- `watching`: one watcher owns the lock and polls locally;
- `event-pending`: a trigger has produced a deduplicated event;
- `notified`: delivery was acknowledged or completed;
- `wake-failed`: bounded delivery retries were exhausted;
- `cancel-requested` / `cancelled`: the operator stopped observation.

An event ID includes the relay name, generation, and reason. Repeated polls of
the same condition therefore cannot repeatedly wake the agent. `rearm`
increments the generation and clears the previous event.

## Trigger Precedence

Use this order so failures are not mistaken for successful completion:

1. failure marker;
2. fatal log pattern;
3. success marker or success log pattern;
4. progress target;
5. monitored process or tmux exit;
6. stale or missing log.

The watcher reads only the configured tail of a log. Match fatal patterns that
appear near termination, and prefer durable markers for authoritative success.

## Delivery Modes

### Codex resume

`codex-resume` executes:

```text
codex exec resume THREAD_ID -
```

The event prompt is passed through stdin. Record the exact thread ID and, when
available, the JSONL transcript path. The watcher waits for `task_complete` and
a quiet period before resuming the thread.

### Generic command

`command` accepts a JSON argv array and writes the event prompt to stdin. This
supports another agent CLI with an explicit resume command. No shell expansion
is performed. Store only trusted argv in the relay state.

### TUI injection

`tui-send-keys` pastes the prompt into a tmux pane and submits it. Record both
the pane identity and PID. The watcher refuses delivery if the pane now hosts a
different command or process. A transcript is required to confirm a new agent
turn whenever possible.

### Inbox

`inbox` writes a compact event prompt to a durable file and exits. It is the
safe fallback when exact-session resume is unavailable.

## Production Checklist

- Put state, logs, markers, and inbox on storage that survives the parent shell.
- Use an absolute Python/script path and absolute monitored paths.
- Confirm the final child environment before starting the long task.
- Run `status` once after `arm`; verify the watcher PID is live.
- Keep `poll_interval_seconds` mechanical and inexpensive.
- Configure a stale threshold longer than legitimate quiet phases.
- Include context paths and a short `wake-instructions` string rather than raw
  context in the event prompt.
- Use `test-event` before unattended operation when delivery is critical.
- Never configure an unbounded wake retry count.

## CLI Operations

```bash
python long_task_relay.py arm ... --background
python long_task_relay.py status --state STATE
python long_task_relay.py test-event --state STATE --reason manual-test --deliver
python long_task_relay.py acknowledge --state STATE
python long_task_relay.py rearm --state STATE --background
python long_task_relay.py cancel --state STATE
```

`acknowledge` records that the agent handled the event. `rearm` starts a new
event generation; use it only after updating the monitored target or underlying
task when necessary.
