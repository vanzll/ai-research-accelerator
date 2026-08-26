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

## Goal mode and relay are mutually exclusive per objective

Treat control ownership per agent conversation and unresolved objective, not
globally across a distributed job. An unfinished Goal and a relay must not own
the same control loop: the Goal keeps that agent active, while a relay requires
an idle conversation that can be resumed only when judgment is needed.

- If the user explicitly selects Goal mode for the unfinished long-running
  objective, do not arm a relay for that objective and do not inject relay
  events into that active Goal session.
- If relay mode is selected, use ordinary mode: arm and verify the watcher,
  then end the agent turn. The watcher owns waiting until it delivers one
  deduplicated event.
- A bounded Goal may repair one already-delivered incident and complete before
  the relay is re-armed. It must not remain active while the relay watches the
  same unresolved objective.
- Different agents may use different modes for distinct role-owned objectives.
  In particular, a coordinator Goal may own bounded cluster recovery through
  first-work validation while ordinary-mode worker agents are woken by their
  own relays for node-local requests. Worker relays must never resume the active
  coordinator Goal or make two agents owners of the same transition.
- Use that hybrid only for a bounded coordinator phase. If the coordinator also
  reaches a long external wait with no actionable work, explicitly hand its
  objective from Goal mode to ordinary relay mode; a blocked Goal is not a
  filesystem notification mechanism and will not self-wake from a new marker.
- If the requested unattended workflow needs both autonomous repair and long
  waits, use an ordinary-mode event-driven relay that starts a fresh or idle
  bounded repair agent per actionable event. Do not keep one Goal alive merely
  to wait.

## Choose the Mode

- Honor an explicit user choice of Goal mode or relay mode before applying the
  remaining routing rules; never silently substitute the other mode.
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
   - for repeated coordinator-to-worker requests, use
     [scripts/shared_agent_dispatcher.py](scripts/shared_agent_dispatcher.py),
     not a fixed one-shot watcher.
4. Arm the watcher with
   [scripts/long_task_relay.py](scripts/long_task_relay.py), verify its state
   and heartbeat, then end the agent turn.
5. When woken, inspect primary evidence and handle exactly one event. Use
   `defer-finalize` so acknowledgement and optional re-arming happen only after
   the delivering watcher exits; re-arm only after advancing the monitored
   target or otherwise removing the handled trigger.

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
- A resumed command cannot directly acknowledge or re-arm the watcher that is
  synchronously waiting for it to exit. Use `defer-finalize`; direct
  `acknowledge`/`rearm` are for an already stopped watcher.

## Shared-Agent Dispatcher

Load `shared-filesystem-agent-coordination` for the complete coordinator/worker
workflow, first-mile order, authority model, message schema, and evidence
semantics. This section defines only the repeated delivery primitive.

For an explicit multi-node coordinator-worker workflow, Node 0 may remain in
Goal mode while each worker uses an ordinary Codex thread plus a token-free
dispatcher. Node 0 atomically publishes a bounded structured request; the
dispatcher validates its sender, target, attempt, nonce, contract hash, and
fencing epoch before running `codex exec resume THREAD_ID -`. It writes an ACK
and terminal result, deduplicates request IDs, then returns to filesystem
waiting without consuming model tokens.

The worker bootstrap must start the dispatcher from its own ordinary thread
using `$CODEX_THREAD_ID`, verify `status=watching`, and then end the turn. Do
not start a worker Goal and do not attach this dispatcher to the coordinator
Goal. Use the immutable attempt-specific manifest created by the coordinator;
never reuse a dispatcher root across attempts.

Treat this initial worker wake path as a separate first-mile bootstrap. Before
the user sends worker prompts, the coordinator must publish the exact tool
checkout, manifest, and final node-specific bootstrap scripts. A worker prompt
must execute that existing script, not merely create a waiter for future code.
The script must place the dispatcher under a durable owner independent of the
agent turn, such as tmux, a scheduler, or a service manager. It may end only
after all acceptance checks hold together: `state.json` exists, the recorded
PID/start identity matches the exact dispatcher and thread/config, the process
is alive under its durable owner, and `status=watching`. A live bootstrap PID,
`waiting`, `waiting-for-tool`, a tmux pane without the dispatcher, or a log line
is not acceptance. The bus cannot repair its own missing dispatcher, so
bootstrap failure must remain in the foreground worker turn until fixed or
explicitly reported; otherwise an external actor must re-enter that worker.

```bash
python shared_agent_dispatcher.py init \
  --root "$ATTEMPT_ROOT" --authority-root "$COORDINATION_FAMILY_ROOT" \
  --experiment-id "$EXP" --attempt A2 \
  --launch-nonce "$NONCE" --science-contract-hash "$CONTRACT_SHA" \
  --fencing-epoch 2 --coordinator-thread-id "$CODEX_THREAD_ID" \
  --node node0=HOST0 --node node1=HOST1

python shared_agent_dispatcher.py start \
  --root "$ATTEMPT_ROOT" --node node1 \
  --thread-id "$CODEX_THREAD_ID" --workdir "$REPO"

python shared_agent_dispatcher.py publish \
  --root "$ATTEMPT_ROOT" --target node1 --action start-node \
  --message-file /path/to/request.txt \
  --completion-predicate 'node1 writes ready or failure evidence'
```

The dispatcher treats accepted-but-incomplete work conservatively: it records
`needs_coordinator` and requires a new request ID rather than replaying an
unknown side effect. It does not execute request text as shell code; an idle
worker agent interprets one bounded request under the frozen contract.
After first-work success or an abandoned campaign, Node 0 runs `close`; worker
dispatchers observe the immutable terminal record and exit without another
agent wake.

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
