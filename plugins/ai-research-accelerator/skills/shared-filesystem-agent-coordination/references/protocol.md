# Shared-Filesystem Agent Coordination Protocol

Read this reference when implementing, reviewing, or recovering a production
shared-filesystem Agent Bus.

## Roles and authority

The coordinator is the only writer of shared source bundles, immutable task
contracts, attempt manifests, and cross-worker requests. It holds a
campaign-scoped lock and publishes a monotonically increasing fencing epoch.
There is no silent coordinator takeover within an attempt.

This protocol assumes the declared agents are trusted writers on the shared
filesystem. Host/thread/nonce/epoch checks provide identity fencing, not
cryptographic authentication. Use ACLs or Node 0 signatures when other
principals can write these paths.

Workers own only their node/session-local execution state and their structured
claims, acknowledgements, results, and events. They never patch shared source
concurrently or command another worker. A worker that needs another node to act
returns `needs_coordinator`; the coordinator publishes a new bounded request to
the intended target.

## Attempt layout

Use one-writer paths instead of a shared Markdown control document:

```text
coordination/TASK/
  campaign-manifest.json
  campaign-terminal.json
  dispatcher/node1/state.json
  active-attempt.json
  attempts/A2/
    manifest.json
    coordinator-owner.json
    inbox/node1/REQUEST_ID.json
    claims/node1/REQUEST_ID.json
    acks/node1/REQUEST_ID.json
    results/node1/REQUEST_ID.json
    invocations/node1/REQUEST_ID.json
    events/node1/SEQUENCE-EVENT.json
    attempt-terminal.json
```

Write a temporary file, flush it, then atomically rename it into place. Inbox,
claim, ACK, result, invocation, event, and terminal records are immutable.
Mutable state files are atomically replaced only by their owning process.

Every attempt record should carry the schema version, task and attempt, nonce,
fencing epoch, protected-contract hash, sender, target, hostname/session
identity, UTC timestamp, request or event ID, action, completion predicate, and
compact evidence paths. Readers reject stale or mismatched records before side
effects. Never persist credentials in the bus.

## First-mile bootstrap

The bus cannot repair a missing worker dispatcher, so bootstrap is a distinct
foreground phase:

Campaign authority remains coordinator-first, but prompt delivery may be
concurrent. This is safe only if the reviewed, pinned worker bootstrap already
exists before prompts are sent and its durable owner performs a token-free,
non-mutating wait until both the finalized campaign manifest and active-attempt
record are present. Missing authority is then a first-mile wait, not worker
readiness and not a blocked Goal. A worker must never infer or manufacture the
missing authority itself.

1. The coordinator prepares a pinned tool checkout, campaign manifest, and
   complete host-specific scripts before dispatchers may accept work. The user
   may already have entered worker prompts when their final scripts are present.
2. A worker prompt executes its existing script; it does not create future
   code. It may arm the reviewed durable authority waiter, but may not return
   until the real dispatcher is accepted.
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

Bootstrap is normally once per campaign, not once per retry. Repeat it only if
the dispatcher implementation, worker host/thread identity, or campaign
authority changes.

## Attempt transitions

An attempt failure is data for the coordinator, not a reason to destroy the
communication channel. Preserve its terminal evidence, clean its owned domain
processes, and return the campaign dispatcher to `watching`.

To advance from A2 to A3:

1. prepare and validate A3 code, manifest, and worker actions while the campaign
   dispatchers remain live;
2. under the campaign lock, compare-and-swap `active-attempt.json` from the
   expected previous epoch to the new root and fencing epoch;
3. let every persistent dispatcher validate and acknowledge the new attempt;
4. dispatch A3 work only after all workers adopted it;
5. keep A2 evidence immutable and reject any late A2 request.

If the installed implementation still binds a dispatcher process to one
attempt root, use a compatibility handoff: publish A3 and its bootstraps first,
ask the live A2 worker Agents to start A3 dispatchers, validate A3 on every
worker, and only then close A2. This make-before-break bridge is mandatory; an
A2 terminal must never remove the only path capable of starting A3.

Do not infer liveness from a readable state file or a zero-exit `status`
inspection. Before migration, classify every matching legacy instance from
its persisted process identity, `process_alive`, `status`, and
`active_request_id`. Dead or stopped records are history and require no close;
a live idle watcher may be closed only after its successor is accepted; a live
busy watcher blocks handoff until its request reaches terminal state. This
prevents both false migration failures and concurrent exact-thread resumes.

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

The only normal dispatcher shutdown is an immutable `GOAL_COMPLETED` directive
published by the exact Node 0 coordinator under the current campaign lock. The
command must compare-and-swap the expected final attempt root, attempt, nonce,
and fencing epoch. It must reference the Goal completion evidence and campaign
identity. Dispatchers validate that record, finish owned
bounded invocations according to contract, write final state, and exit without
another Agent wake.

Attempt terminal, request failure, idle timeout, trainer exit, missing next
attempt, or temporary coordinator loss must not trigger dispatcher shutdown.
When authority is unavailable or ambiguous, remain alive in a fenced
non-executing wait. If the dispatcher process crashes, its durable supervisor
restarts it; a crash is not campaign completion. Archive compact bus metadata
after `GOAL_COMPLETED`; do not delete formal lineage.
