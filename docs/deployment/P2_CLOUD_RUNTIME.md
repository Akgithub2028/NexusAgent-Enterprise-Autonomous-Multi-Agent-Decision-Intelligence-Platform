# P2 cloud runtime, bounded memory and structured audit

Implemented from `5ce044b2dfec6b40dd2a7cc05401017975dc062d` on 2026-10-03.
[Validation evidence](P2_VALIDATION.json) records the final checks. No cloud resources
are provisioned in this phase; P3 is the next phase and remains unstarted.

## Container entrypoint and lifecycle

```bash
.venv/bin/python -m decision_agent.cloud
```

The launcher validates `PORT` as a decimal TCP port in 1–65535, defaults only an absent
value to 8080, and binds `0.0.0.0` with one Uvicorn worker and no reload. It uses
`create_deployment_app(Settings())`, preserving private fail-closed defaults and the
P1 public-demo resolver/guard. It never calls the localhost configuration adapter.
Invalid launch configuration returns exit code 2 with a fixed JSON error and no input
values. `K_REVISION`, when present, supplies validated revision metadata.

The existing formal lifespan still builds and publishes the executor only after
complete startup, rolls back partial resources, and revokes execution before LIFO
cleanup. Bootstrap failure keeps `/ready` and execution unavailable while `/health`
and the UI remain available. Lifecycle logs report starting, ready, failed and stopped
with fixed error codes. Uvicorn's graceful request drain is limited to eight seconds;
remaining requests are cancelled before lifespan cleanup. Actual SIGTERM shutdown of
the launcher is tested with an owned resource and deterministic builder.

Readiness deliberately retains its existing contract: completed bootstrap plus the
registered required checks. No continuous remote SQL/vector/provider health guarantee
is added. `/health` remains independent of remote dependencies. Existing opt-in
preflight seams should be used for release validation in later phases. Missing required
checks still report unavailable; no placeholder successful remote checks are installed.

## Memory retention and concurrent requests

Set `DECISION_AGENT_MEMORY_MODE=in_memory` explicitly for demo V1. The default remains
`disabled`. `DECISION_AGENT_MEMORY_MAX_SESSIONS` defaults to 1000, accepts 1–100000 and
bounds each configured in-memory store. Direct store construction also defaults to 1000.
It does not bound Redis; Redis is deferred.

New-session writes sweep all expired sessions under the store lock before admission.
`sweep_expired()` is also available for explicit cleanup. No timer/background thread is
required: idle expired entries remain bounded and are reclaimed before capacity can
block a new session. Live sessions are never evicted. At capacity, a new session raises
`SessionMemoryCapacityError("memory_capacity_exceeded")`; existing sessions can still
append/compact, and duplicate retries remain idempotent. The executor maps rejected
persistence to `store_failure`, preserving a grounded result without promising stored
history. UI memory status already displays persistence failure.

TTL, max turns, compaction lineage and optimistic versions remain unchanged. Parallel
requests for the same session do not silently overwrite: one successful append advances
the version and a stale append reports `version_conflict`. Clearing a session still
requires its expected version. P1 tenant/verified visitor/session-label hashing is retained.
The capacity counter is not keyed by raw client identity.

History can disappear after expiry, restart or rollout. A stable signing key preserves
visitor identity, not process memory. One maximum Cloud Run instance does not guarantee
history across revisions or temporary overlap. This limitation is now visible in the
Workbench. No new persistence or Redis infrastructure was introduced.

## Mandatory audit output

`DECISION_AGENT_AUDIT_MODE` is explicitly `file` (default) or `stdout`.

- `file` retains the existing JSONL writer, fsync, hash chain, committed-tip anchor and
  tamper verification. Outside test environments it still requires `AUDIT_LOG_PATH`.
  The localhost demo forces file mode and its external audit path, even if the caller
  supplied stdout mode. Test-only missing-file composition still uses the existing
  in-memory audit sink.
- `stdout` uses `StdoutAuditSink` and does not require or write `AUDIT_LOG_PATH`.
  Each event is a single JSON line containing `event`, `severity`, `runtime` and `audit`.
  The `audit` object remains the closed `AuditEvent` schema, without business payloads.
  Writes are locked, followed by an explicit flush, and short writes are failures.
  Failure poisons the sink: future writes fail rather than continuing an uncertain chain.
  Closing the runtime closes the sink, never the process's stdout stream.

Audit append failures raise fixed `AuditChainError` codes without rendering stream
exception text. Existing provider governance blocks transport if admission audit fails;
completion-audit failure cannot return provider output. The formal response-release
boundary also blocks answers/citations when its audit cannot be written. This mandatory
path never goes through best-effort Python logging.

A flushed stream proves local acceptance, not durable Cloud Logging delivery. The hash
chain is per sink in one process/revision; its process/release metadata identifies that
boundary. It is not a global ordered chain or cloud delivery guarantee. Cloud retention,
access controls and export policy remain deployment configuration in later phases.

## Structured logging and release metadata

The launcher configures INFO-level JSON output with a real handler/formatter. Approved
trace payloads and lifecycle events are structured objects, not double-encoded messages.
Arbitrary library messages, exception text/tracebacks and access URLs are omitted; other
records emit fixed diagnostic events with severity. Uvicorn access logging is disabled.
A logging-output failure stays best effort and suppresses Python logging's unsafe error
fallback; it cannot replace or satisfy a mandatory audit write.

`DECISION_AGENT_RELEASE_ID` and `DECISION_AGENT_CORPUS_RELEASE_ID` default to `unversioned`;
`DECISION_AGENT_RUNTIME_REVISION` defaults to `local` and the launcher uses `K_REVISION`
when provided. These fields accept only 1–128 ASCII letters/digits/underscore/dot/hyphen.
Do not put connection URLs, credentials, queries, prompts, rows, cookies or visitor
identities in them. A generated process identifier correlates audit and trace logs.
Image/corpus manifest wiring is P3/P5; `unversioned` is not a verified release claim.

Example configuration additions for an eventual cloud service (P1's required provider,
origin/signing, database, Milvus and corpus configuration must also be supplied):

```dotenv
DECISION_AGENT_AUDIT_MODE=stdout
DECISION_AGENT_MEMORY_MODE=in_memory
DECISION_AGENT_MEMORY_MAX_SESSIONS=1000
DECISION_AGENT_RELEASE_ID=release-001
DECISION_AGENT_CORPUS_RELEASE_ID=m2c1-release-001
PORT=8080
```

This is not yet a ready-to-deploy image: baked models/offline reranker and CPU image
strategy are P3; managed vector and Cloud SQL transport/provisioning changes are P4.
