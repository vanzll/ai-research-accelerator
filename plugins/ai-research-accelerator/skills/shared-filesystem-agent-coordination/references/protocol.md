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

Workers own only their node-local execution state and their structured
claims, acknowledgements, results, and events. They never patch shared source
concurrently or command another worker. A worker that needs another node to act
returns `needs_coordinator`; the coordinator publishes a new bounded request to
the intended target.

## Attempt layout

Use one-writer paths instead of a shared Markdown control document:

```text
coordination/TASK/
  protected-task-contract.json
  campaign-manifest.json
  campaign-terminal.json
  result-schema.json
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
   the Agent turn. The owner restarts an abnormally exited campaign supervisor;
   that supervisor restarts an abnormally exited dispatcher.
4. Acceptance is conjunctive: read state only from the canonical expected
   campaign root; require exact campaign ID, protected-contract hash,
   coordinator authority, current attempt root/ID/nonce/fencing epoch,
   node/host, dispatcher generation, PID/start identity and execution adapter;
   then require process alive, durable owner alive, `agent_mode=fresh`, and
   `status=watching`.
5. Run two real harmless deliveries per worker. Each must create the expected
   claim, ACK, invocation, terminal result, and final re-armed `watching` state.

Process identity checks must execute on the process's host. Each worker writes
an atomic readiness attestation containing the locally verified supervisor and
dispatcher identities, adapter config, status, and timestamp. Node 0 accepts it
only within a short TTL and still requires end-to-end deliveries. Never compare
a remote PID against Node 0's `/proc`; PID values are namespace-local and may
collide.

Do not weaken this to “bootstrap alive OR dispatcher waiting.” A transient
bootstrap can disappear when the Agent exits and creates a self-bootstrap
deadlock.

Likewise, do not weaken it to “any dispatcher on this node is healthy.” An old
campaign can remain correctly alive and `watching` while having no authority
over the new campaign. Never scan for an arbitrary state file or reuse a
readiness record across campaign roots or protected-contract hashes. Bring up
and validate the expected campaign with make-before-break, then retire an old
campaign only under its own closure authority.

Bootstrap is normally once per campaign, not once per retry. Repeat it only if
the dispatcher implementation, worker host identity, execution adapter, or
campaign authority changes. A new TUI conversation is irrelevant in fresh
mode.

Cache successful delivery acceptance by the dispatcher tool hash, durable
owner identity, worker host, execution adapter, and campaign authority. Reuse
it across task attempts only while a fresh node-local health attestation proves
the current dispatcher generation and process identity. A supervisor restart
invalidates process-level acceptance and requires the harmless delivery checks
again. Do not spend Agent invocations re-proving an unchanged healthy transport
on every retry.

## Worker execution adapters

Use `fresh` by default. For every accepted request, the persistent dispatcher
starts a new ephemeral Agent process, passes the bounded request plus durable
context paths on stdin, captures one schema-validated result, and exits that
Agent. The dispatcher, not the Agent, owns waiting and request sequencing.
Repository handoffs and shared records are memory; conversation history is not.

`resume` is an opt-in compatibility adapter. It requires a current thread ID,
transcript path, and matching Agent home namespace. Treat that binding as an
expiring lease: drain active work, stop the old dispatcher, restart it with the
new binding under the same campaign owner, validate the new process identity,
and complete two harmless deliveries before use. A
missing rollout yields `needs_coordinator`; it must never terminate the
campaign dispatcher. Never use `--last` or hard-code a thread in a reusable
bootstrap.

Freeze the Agent executable, Agent home path, work directory, adapter mode, and
additional CLI arguments in dispatcher state. Do not persist credentials.
Reject additional arguments that can replace the dispatcher-owned prompt,
output schema, output path, or ephemeral lifecycle.

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

## Design bounded actions and validators

Keep requests small enough to have one unambiguous completion predicate:

- `preflight` runs a pinned, read-only script and returns a versioned result;
- `start` launches the exact owned process, verifies early local identity, and
  returns `launched` without waiting for the domain task to finish;
- a token-free watcher observes process and milestone evidence;
- `diagnose` or `repair` wakes an Agent only when evidence requires judgment.

The coordinator owns shared validator code. Workers execute the same pinned
implementation rather than generating node-specific parsers in prompts. A
validator must read dynamic attempt and fencing values from the authority
record, validate explicit schema versions, compare canonical identities or
content hashes, and reject unknown fields conservatively. It must not hard-code
the current retry, assume an undocumented evidence shape, or compare a symlink
spelling when the runtime intentionally canonicalizes the path.

Keep prompts thin: identify the role, canonical contract, active authority,
request, result schema, deterministic command, permissions, and stopping rule.
When the project maintains a progress document or runbook, put historical
incidents and operational explanation there; neither belongs duplicated inside
every request. These human documents are optional and are not bus authority.

## Request lifecycle

1. The coordinator publishes one immutable bounded request.
2. The dispatcher validates authority, active attempt, fencing epoch, target,
   host, and request ID.
3. It atomically claims the request and launches one bounded fresh Agent by
   default; resume mode first proves the selected thread is idle.
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
restarts it. If the supervisor crashes, the node-level durable owner restarts
it; neither crash is campaign completion. Archive compact bus metadata
after `GOAL_COMPLETED`; do not delete formal lineage.
