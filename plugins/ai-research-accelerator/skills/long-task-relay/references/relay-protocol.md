# Long-Task Relay Protocol

## Control-mode ownership

A relay assumes that no model session continuously owns the unresolved wait.
The bootstrap agent arms the relay in ordinary mode, verifies it once, and
ends its turn. The watcher later resumes an idle conversation or starts an
explicit bounded agent invocation for one actionable event.

Do not attach a relay to an active unfinished Goal for the same objective. Goal
mode is itself a persistent control loop and cannot hand that objective to a
dormant relay without creating duplicate ownership. This rule is scoped to a
conversation and objective, not an entire distributed job: a coordinator Goal
may own bounded global recovery while separate ordinary-mode worker agents use
relays for node-local requests. A worker relay must target only its worker
conversation. A repair agent woken by a relay may use a bounded Goal for that
incident only if it completes before the relay is re-armed.

The hybrid is appropriate only while the coordinator Goal owns a bounded,
active recovery phase. Shared-file changes do not wake a blocked Goal. If the
coordinator must enter a long quiet wait, perform an explicit ownership handoff:
end the Goal control loop, arm an ordinary coordinator relay, verify it, and
then let that relay resume an idle coordinator agent on the next event. Never
leave both owners active during the handoff.

For a coordinator-worker workflow, use a star topology. The coordinator writes
an immutable request into the target worker's inbox. A separately reviewed
token-free inbox dispatcher validates and deduplicates the request, then wakes
the idle worker agent; it never interprets or executes arbitrary instructions.
The worker acknowledges the request, performs one bounded task, emits a
structured result, and ends its turn. The dispatcher uses an at-least-once wake
protocol: it atomically claims the request with a bounded lease, but does not
mark it processed until a terminal result exists. A wake that dies before ACK
may be redelivered with the same request ID after the claim expires. An ACK
without a terminal result becomes an `incomplete-request` event for the
coordinator and is never an automatic task retry. After `failed` or
`needs_coordinator`, only the coordinator may issue a new request ID. Workers
report to the coordinator rather than issuing commands directly to one another.

The base `long_task_relay.py` watcher observes fixed markers, logs, progress,
PIDs, and tmux state and handles one event per generation. It is not a repeated
structured-inbox consumer. Use `scripts/shared_agent_dispatcher.py` for that
role. It validates coordinator identity, target node, attempt, nonce,
scientific-contract hash, fencing epoch, and request ID; tracks claims,
acknowledgements, and terminal results; and repeatedly resumes the exact idle
worker thread. A fixed one-shot relay remains appropriate for one already
selected event outside a coordinator-worker message bus.

The dispatcher uses an immutable attempt-local `agent-bus-manifest.json` plus
an authority-root `active-agent-bus.json` advanced under a coordinator lock.
Workers and publishers re-read the active record, so a higher fencing epoch
stops superseded dispatchers and rejects old publishers. Node
0's hostname and Goal thread ID are frozen in that manifest; only that thread
may publish, and it cannot publish to itself. A worker owns only its
claim, ACK, result, and dispatcher state paths. An accepted request that loses
its agent invocation is terminally reported as `needs_coordinator`; automatic
re-execution is forbidden because its side effects may already exist. Node 0
must inspect evidence and issue a new request ID. This conservative policy is
at-most-once for bounded tasks after acceptance, while publication and inbox
observation remain repeatable and deduplicated.

Before delivery, a renewable claim lease permits recovery only while no agent
invocation record exists. Each actual resume runs under a gate-controlled
helper process group whose PID start-token is persisted before the gate opens.
The launcher publishes its own PID identity before `exec` and carries a shared
authority-lock descriptor into the actual Codex process. Thus epoch takeover
and close are quiescent even if the helper is killed. The helper writes ACK
only after the launcher identity is durable and writes the terminal result
itself. Dispatcher restart therefore observes the same helper/result rather
than replaying work; stop terminates the full helper group and records
`needs_coordinator`.

The dispatcher resumes a worker only after its JSONL transcript records
`task_complete` and remains quiet. The resumed turn is constrained by a JSON
result schema (`succeeded`, `failed`, or `needs_coordinator`), and its terminal
record is written by the dispatcher even when the agent process fails. The
dispatcher itself is a detached, token-free process with an atomic heartbeat;
future requests therefore do not require a human to reopen the worker Codex.
The coordinator closes the bus with one immutable `terminal.json`; dispatchers
stop mechanically after their current bounded invocation returns.

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

- Confirm that the target task is in ordinary mode and has no active unfinished
  Goal owning the same objective.
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
- For shared-agent dispatch, create one immutable manifest per attempt, record
  each worker's exact `$CODEX_THREAD_ID`, verify the transcript path, and run
  `status` once before the bootstrap turn exits.
- Publish only bounded node-local requests. Source changes, asset publication,
  attempt advancement, and scientific decisions stay with the coordinator.

## CLI Operations

```bash
python long_task_relay.py arm ... --background
python long_task_relay.py status --state STATE
python long_task_relay.py test-event --state STATE --reason manual-test --deliver
python long_task_relay.py defer-finalize --state STATE --rearm
python long_task_relay.py acknowledge --state STATE
python long_task_relay.py rearm --state STATE --background
python long_task_relay.py cancel --state STATE
```

`acknowledge` records that the agent handled the event. `rearm` starts a new
event generation; direct use requires the watcher to have exited. A resumed
agent should instead run `defer-finalize`, optionally with `--rearm`; its helper
waits for the delivering watcher to exit before acknowledging and starting the
next generation. Deferred finalization is fenced by generation, event ID, and
delivering watcher PID; repeated requests reuse a live matching helper, and a
late helper cannot modify a newer generation. Re-arm only after updating the
monitored target or resolving a persistent trigger, otherwise the same
condition will fire immediately.
