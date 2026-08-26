# Shared-Filesystem Agent Coordination Protocol

Read this reference when implementing, reviewing, or recovering a production
shared-filesystem Agent Bus.

## Roles and authority

The coordinator is the only writer of shared source bundles, immutable task
contracts, attempt manifests, and cross-worker requests. It holds an
experiment- or task-scoped lock and publishes a monotonically increasing
fencing epoch. There is no silent coordinator takeover within an attempt.

Workers own only their node/session-local execution state and their structured
claims, acknowledgements, results, and events. They never patch shared source
concurrently or command another worker. A worker that needs another node to act
returns `needs_coordinator`; the coordinator publishes a new bounded request to
the intended target.

## Attempt layout

Use one-writer paths instead of a shared Markdown control document:

```text
coordination/TASK/
  active-attempt.json
  attempts/A2/
    manifest.json
    coordinator-owner.json
    dispatcher/node1/state.json
    inbox/node1/REQUEST_ID.json
    claims/node1/REQUEST_ID.json
    acks/node1/REQUEST_ID.json
    results/node1/REQUEST_ID.json
    invocations/node1/REQUEST_ID.json
    events/node1/SEQUENCE-EVENT.json
    terminal.json
```

Write a temporary file, flush it, then atomically rename it into place. Inbox,
claim, ACK, result, invocation, event, and terminal records are immutable.
Mutable state files are atomically replaced only by their owning process.

Every record should carry the schema version, task and attempt, nonce, fencing
epoch, protected-contract hash, sender, target, hostname/session identity, UTC
timestamp, request or event ID, action, completion predicate, and compact
evidence paths. Readers reject stale or mismatched records before side effects.
Never persist credentials in the bus.

## First-mile bootstrap

The bus cannot repair a missing worker dispatcher, so bootstrap is a distinct
foreground phase:

1. The coordinator prepares a pinned tool checkout, manifest, and complete
   host-specific scripts before workers are prompted.
2. A worker prompt executes its existing script; it does not create a future
   waiter or return while dependencies are absent.
3. The script starts the dispatcher under a durable process owner that survives
   the Agent turn.
4. Acceptance is conjunctive: state file present, expected PID/start identity,
   exact host/thread/config, process alive, durable owner alive, and
   `status=watching`.
5. Run two real harmless deliveries per worker. Each must create the expected
   claim, ACK, invocation, terminal result, and final re-armed `watching` state.

Do not weaken this to “bootstrap alive OR dispatcher waiting.” A transient
bootstrap can disappear when the Agent exits and creates a self-bootstrap
deadlock.

## Request lifecycle

1. The coordinator publishes one immutable bounded request.
2. The dispatcher validates authority, active attempt, fencing epoch, target,
   host, and request ID.
3. It atomically claims the request and resumes the exact idle Agent thread.
4. The invocation writes an ACK only after the Agent process is actually
   spawned.
5. The Agent handles one request and returns a structured terminal status:
   `succeeded`, `failed`, or `needs_coordinator`.
6. The dispatcher persists the result, marks the request processed, and returns
   to `watching`.

At-least-once delivery is safe only with request-ID deduplication and idempotent
actions. Delivery may retry before ACK after proving the prior invocation is
gone and its claim expired. An ACK without a terminal result is ambiguous; do
not automatically replay it. The coordinator must issue a new request after
diagnosis.

## Repair loop

The protected task contract defines what must not change. For scientific or
training workflows, include algorithm/objective, models, data, batching,
optimizer, precision, sampling, parallel topology, evaluation, and checkpoint
semantics. For other workflows, freeze the equivalent behavior-defining
inputs.

An unattended operational repair loop is:

1. preserve failure evidence and return a structured diagnosis;
2. let the coordinator classify the change as operational or semantic;
3. add a regression test for an operational bug;
4. publish a new shared commit and new attempt/nonce without rewriting failed
   lineage;
5. revalidate the protected contract before dispatching the retry;
6. stop at the declared first-work or completion gate.

Workers may fix node-local environment activation, process ownership, service
readiness, or transport setup only when the protected semantics cannot change.
Shared fixes remain coordinator-owned. Ambiguous changes require user approval.

## Monitoring and closure

Use a token-free monitor for dispatcher heartbeat, state, queue depth, claims,
ACKs, results, invocation identity, and stale/failure events. Do not keep Agents
polling and do not wake every worker to ask for status.

Interpret states conservatively:

- `watching` plus no active request is healthy idle;
- `agent-active` means one validated request is executing;
- terminal result plus `watching` proves that request completed and re-armed;
- stale heartbeat, failed delivery, or `needs_coordinator` requires attention;
- bus readiness never substitutes for domain workload evidence.

When the coordinator publishes an immutable close record, dispatchers finish
owned work, write final state, and exit without another Agent wake. Archive
compact bus metadata; do not delete formal lineage merely because the workflow
completed.
