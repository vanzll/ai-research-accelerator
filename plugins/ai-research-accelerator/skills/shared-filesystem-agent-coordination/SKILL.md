---
name: shared-filesystem-agent-coordination
description: Coordinate coding agents through a reliable shared-filesystem message bus with one coordinator, relay workers, exact-thread wakeups, atomic request/ACK/result records, fencing, monitoring, and bounded repair. Use when agents on different machines or sessions must collaborate without direct messaging.
---

# Shared Filesystem Agent Coordination

Use shared storage as a message transport, not as a concurrently edited chat
document. The default topology is a star:

- one coordinator Agent owns global decisions, shared artifacts, and requests;
- each worker uses an ordinary Agent thread plus a token-free dispatcher;
- workers execute bounded local requests and return structured evidence;
- worker-to-worker needs return to the coordinator for routing.

This creates command-and-report collaboration, not unrestricted peer chat.

## Assign control ownership

Use Goal mode only for the coordinator's bounded objective. Worker threads stay
in ordinary mode so a dispatcher can resume their exact thread only when a
request requires judgment. Deterministic supervisors own waiting and already
authorized transitions. Never attach a relay to an active Goal for the same
objective.

Freeze an immutable task contract before granting repair authority. Name the
semantics and artifacts agents may not change. The coordinator may authorize
operational repairs that preserve that contract; workers may repair strictly
node-local operational state. Any uncertain or semantic change requires user
approval.

## Scope lifetime to the campaign

Bind each worker dispatcher to the coordinator's campaign/Goal, not to one
retry attempt. Attempts are replaceable execution lineages under one protected
contract; the Agent communication channel must survive their failure. Keep one
campaign-level dispatcher registration and heartbeat per worker, while storing
requests, claims, ACKs, results, and terminal evidence under immutable
attempt-specific paths.

An attempt terminal returns the dispatcher to `watching`. Its only normal exit
condition is a fenced `GOAL_COMPLETED` directive explicitly published by the
exact Node 0 host and Goal thread. Request failure, attempt failure, idle
time, workload exit, or temporary coordinator loss must not close it; enter a
safe non-executing wait when authority is unavailable. The coordinator advances
an atomic `active-attempt.json` and fencing epoch, and workers accept the new
attempt only after validating its immutable manifest. If a legacy dispatcher is
attempt-scoped, use make-before-break: start and validate the next dispatcher
through the old bus, then close the old bus. Never close the only wake path
before its successor is operational.

During that handoff, a successful `status` command proves only that persisted
state is readable; it does not prove the legacy process is alive. Classify the
old instance using `process_alive`, `status`, and `active_request_id` together:
ignore stopped/dead history, close a live idle `watching` instance only after
the campaign successor is ready, and block migration while a live legacy
request is active. Never let two dispatchers concurrently resume the same
exact thread.

## Bootstrap coordinator-first

Coordinator-first is an authority ordering rule, not necessarily a manual
prompt ordering rule. The user may send all node prompts concurrently only
when the final pinned tool and worker-specific bootstrap scripts already exist.
Before Node 0 publishes the finalized campaign manifest and active-attempt
record, each worker bootstrap may start a durable token-free wait, but it must
not start the dispatcher, accept requests, mutate shared authority, or report
readiness. After authority appears, it validates and adopts it automatically.

The first-mile logical order is mandatory:

1. The coordinator publishes and validates the pinned dispatcher tool,
   immutable campaign manifest, and final worker-specific bootstrap scripts.
2. Each worker executes its existing script and starts the dispatcher under a
   durable owner independent of the Agent turn, such as tmux, a scheduler, or a
   service manager. If prompts were sent concurrently, this owner performs only
   the bounded authority wait until step 1 completes.
3. Worker acceptance requires all of: persisted `state.json`, matching
   PID/start identity and exact thread/config, `process_alive=true`, and
   `status=watching`.
4. The coordinator runs two harmless `publish -> resume -> result -> watching`
   round trips per worker, proving first delivery and re-arming. Repeat this
   only when dispatcher code, host/thread registration, or campaign authority
   changes, not for every attempt.
5. Only after every worker passes may the workflow publish real tasks.

A bootstrap PID, `waiting`, `waiting-for-tool`, a tmux pane without the target
dispatcher, or a log line is not readiness. A missing dispatcher cannot wake
the Agent needed to install itself; repair that failure in the foreground
worker turn or through an external actor.

## Use structured, fenced messages

Use campaign-scoped atomic JSON records for dispatcher registration, authority,
heartbeat, active-attempt selection, and campaign close. Keep each attempt's
manifest, inbox requests, claims, ACKs, terminal results, and events under its
own immutable path. The coordinator is the only request publisher. Each worker
owns its claim, ACK, result, and status paths. Preserve history and reject stale
attempts, epochs, nonces, hosts, threads, senders, and request IDs.

Delivery is at-least-once; processing must be idempotent. A request retry uses
a new request ID. If an accepted request loses its Agent before a terminal
result, report `needs_coordinator` rather than replaying an unknown side effect.
Watchers validate requests but never execute request text as shell code.

The default threat model trusts the shared storage writers and uses immutable
records plus host, thread, nonce, contract, and epoch validation. If unrelated
or adversarial principals can write the bus, enforce filesystem ACLs or verify
Node 0 signatures; matching JSON fields alone are not cryptographic
authentication.

## Use the campaign CLI

The reviewed dispatcher separates stable campaign state from replaceable
attempt buses:

```bash
python shared_agent_dispatcher.py campaign-init \
  --root "$CAMPAIGN_ROOT" --authority-root "$AUTHORITY_ROOT" \
  --attempts-root "$ATTEMPTS_ROOT" --campaign-id "$CAMPAIGN_ID" \
  --science-contract-hash "$CONTRACT_SHA" \
  --coordinator-thread-id "$NODE0_THREAD" \
  --node node0=HOST0 --node node1=HOST1

python shared_agent_dispatcher.py campaign-activate \
  --root "$CAMPAIGN_ROOT" --attempt-root "$A3_ROOT" \
  --expected-previous-epoch 2

python shared_agent_dispatcher.py campaign-start \
  --root "$CAMPAIGN_ROOT" --node node1 \
  --thread-id "$WORKER_THREAD" --workdir "$WORKDIR"
```

`campaign-activate` is a compare-and-swap. The first activation expects epoch
`-1`; later activations name the currently active epoch. Goal closure also
requires the expected final root, attempt, nonce, and epoch. Do not use the old
attempt-scoped `start` command for a new campaign.

## Interpret evidence correctly

- `AGENT_BUS_READY` proves command delivery, Agent execution, result return,
  and dispatcher re-arming.
- Per-request dispatch/ACK/result proves only that bounded action's lifecycle.
- Domain milestones require their own primary evidence; an Agent Bus smoke does
  not prove that training, deployment, evaluation, or another workload started.
- `watching` with no active request is healthy idle capacity, not failure or a
  blocked Goal.

Monitor heartbeats, inbox depth, claims, ACKs, results, invocation identity,
and stale/failure events mechanically. Wake an Agent only for an actionable
request or anomaly. Historical failures remain preserved but are scoped by the
active attempt, fencing epoch, and expected request IDs.

Read [protocol.md](references/protocol.md) before implementing a production
bus, autonomous repair loop, or remote-Agent prompt. Use `long-task-relay`'s
reviewed `shared_agent_dispatcher.py` rather than rewriting repeated delivery.
