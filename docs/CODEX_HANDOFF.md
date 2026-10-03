# Codex implementation handoff

Verified against the repository on 2026-10-03. This is a documentation-only handoff;
no P2 implementation was performed while preparing it.

## Checkout and authoritative evidence

- Repository: `Akgithub2028/NexusAgent-Enterprise-Autonomous-Multi-Agent-Decision-Intelligence-Platform`.
- Workspace: `/media/aayaann-kausar/New Volume1/Project Enhancements-Deployements`.
- Repository is the `NexusAgent-Enterprise-Autonomous-Multi-Agent-Decision-Intelligence-Platform`
  child directory. Run repository commands there, not in the workspace parent.
- Inspected implementation HEAD: `71732c7e8f9d5db2534b58925d125b2a9f56f4c4`
  (`feat: add isolated public demo identity and bounded admission`).
- Branch `main`; working tree clean before this handoff change; `origin/main` matched HEAD.
- P0 commit: `635a8ecc697754d798376626b0380f06d60e4cbf`.
- Original audited baseline: `2e2b34c220158c1711409ddb1335fba00fbe375f`.
- No applicable `AGENTS.md` was found during inspection.
- Prior user instructions authorize committing and pushing completed changes. Existing
  `gh` authentication works; do not put credentials in documents, commands, remotes or Git.
- Work within this workspace. Do not delete files or directories outside it.

Read [deployment status](deployment/README.md), [phase plan](deployment/IMPLEMENTATION_PLAN.md),
[P1 contract](deployment/P1_PUBLIC_DEMO.md) and [P1 evidence](deployment/P1_VALIDATION.json)
first. [P0 audit](deployment/P0_AUDIT.md) and its reports are historical evidence, not
current dependency findings. Directory READMEs and the
[directory index](deployment/DIRECTORY_INDEX.md) explain source seams; the
[manifest](deployment/DIRECTORY_MANIFEST.json) records their source fingerprints.
Recheck source when a fingerprint or implementation has changed.

## Objective and current phase boundary

Deploy NexusAgent as one Cloud Run container containing FastAPI, the existing Workbench,
LangGraph, CPU BGE retrieval/reranking and internal stdio MCP. Externalize synthetic
MySQL to Cloud SQL and vectors to Zilliz; retain local BM25/parent metadata in the same
immutable corpus release. Separate ingestion into a Cloud Run Job. Add Secret Manager,
structured Cloud Logging, Artifact Registry and GitHub Actions deployment through OIDC.

V1 targets a public synthetic-data demo with fixed least-privilege grants and isolated
visitors. In-memory history is intentionally ephemeral; Redis is deferred. There is
no deployed cloud service, application Dockerfile, cloud resource provisioning, CD
workflow or verified live demo URL yet.

P0 and P1 are complete. P2–P7 are planned. The latest instruction is to prepare this
handoff before further implementation; do not infer permission to start P2 from this file.

## Architecture that exists now

```text
FastAPI: / + /assets Workbench, health/readiness, execution API
  -> FormalRequestExecutor + scoped session context
  -> LangGraph routing/coordinator/skills
     -> Knowledge: BGE embeddings + Milvus + BM25/RRF + parent expansion + BGE reranker
     -> Data: owned stdio MCP subprocess -> SQLGlot validation -> SQLAlchemy/PyMySQL
     -> Mixed: controlled knowledge/data workflow
  -> evidence selection/reviewer -> grounded answer and citations
```

- `src/decision_agent/main.py` constructs `Settings()` and calls
  `create_deployment_app(settings)`. Runtime construction remains deferred to lifespan.
- `api/runtime.py` and `application/bootstrap.py` own publication, revocation and
  `AsyncExitStack` cleanup. `application/configured_runtime.py` composes the real runtime.
  Failed bootstrap leaves execution/readiness unavailable rather than publishing a
  partial executor. Shutdown revokes the executor and closes owned resources.
- `/health` is liveness. `/ready` checks runtime state and registered required checks;
  it is not proof of continuous remote dependency health. MCP schema discovery does
  not itself establish SQL connectivity. Explicit preflight seams already exist.
- Serving calls retrieval initialization with `ingest_corpus=False`; the explicit
  ingestion command uses `initialize_for_ingestion()`. Serving still initializes the
  vector store and can create missing collections/indexes. Reader-only provisioning
  separation remains P4 work.
- Retrieval loads local parent/child JSONL and requires exact agreement between local
  child IDs and vector IDs. Default generated corpus is under
  `datasets/enterprise_kb/m2c1/generated` (12 documents, 36 parents, 101 children).
  BM25 and parent expansion are not externalized to Zilliz.
- Milvus currently permits HNSW only, with schema/filter validation. Managed AUTOINDEX
  is not implemented. Changing the endpoint alone is insufficient.
- BGE loading/inference already use `asyncio.to_thread` and per-model inference locks.
  Embeddings have cache/offline controls; equivalent reranker controls remain P3 work.
- MCP remains internal and uses the installed interpreter/module through stdio. The
  subprocess environment is explicitly whitelisted in
  `mcp_client/enterprise_data_client.py`. Keep stdout exclusively for MCP protocol.
- SQL currently uses TCP `mysql+pymysql`, lazy connections and guarded read queries.
  Cloud SQL Unix sockets, their child-environment propagation and pool configuration
  remain P4 work.
- Non-test configured runtime requires `audit_log_path`. `security/audit.py` provides
  JSONL hash chaining, fsync and anchors/tamper detection. Governance audit failures
  fail closed; tracing is best effort. No cloud stdout audit selection exists yet.
- In-memory memory has locks, TTL, retained-turn limits, deduplication and optimistic
  versions, but no total-session bound or global expiry sweep. Expiration occurs on
  access. Concurrent executions can conflict on the same session version.
- Docker Compose starts MySQL, etcd, MinIO and Milvus only; no app or Redis service.

## Completed phases, changed files and decisions

### P0: audit and baseline

Created the deployment audit, P0 baseline/dependency evidence, P0–P7 implementation
plan, directory index/manifest and 52 directory README maps. No runtime deployment
behavior was added. The maps now cover 54 directories following P1 additions.

P0 established that the formal runtime should be reused, that serving and ingestion
were already separate for chunk upserts, and that managed Milvus/Cloud SQL required
adapter work. It also found dependency advisories subsequently remediated in P1.

### P1: public identity and admission

| Files | Purpose |
| --- | --- |
| `src/decision_agent/api/public_demo.py` (new) | Visitor HMAC cookie, fixed resolver, bounded admission/ASGI body guard and deployment factories. |
| `src/decision_agent/main.py` | Select the explicit deployment factory while preserving deferred bootstrap. |
| `src/decision_agent/config/settings.py`, `.env.example` | Private default, validated public configuration and limiter settings. |
| `src/decision_agent/security/models.py`, `security/__init__.py` | Dedicated demo principal/authentication provenance and factory export. |
| `src/decision_agent/api/routes.py` | Describe new body/admission error responses in the API. |
| `src/decision_agent/web/app.js` | Bootstrap the visitor before execution and handle authentication/capacity failures. |
| `tests/unit/api/test_public_demo.py` (new) | 52 focused public-demo/regression cases, also selected by offline integration. |
| `tests/unit/application/test_configured_runtime_bootstrap.py` | Replace brittle entrypoint AST expectations with lifecycle behavior checks. |
| `pyproject.toml`, `requirements.lock` | Compatible advisory remediation and minimum dependency floors. |
| `docs/deployment/P1_PUBLIC_DEMO.md`, `P1_VALIDATION.json` (new) | Implemented API/configuration contract and reproducible validation evidence. |
| Root/affected directory READMEs and deployment index/manifest/plan | Current phase status, file maps and refreshed fingerprints. |

Design decisions:

- Explicit `public_demo` is opt-in; private mode retains the rejecting security
  resolver. The loopback local-demo resolver is not widened for public hosting.
- Every visitor gets a distinct signed subject under one fixed demo tenant. A shared
  anonymous principal would allow shared session labels to expose another visitor's history.
- Cookie authorization grants are entirely server-defined. The HMAC format has no
  client-selected claims/algorithm and does not use PyJWT.
- Same-origin checks protect cookie-authenticated expensive POSTs. They do not provide
  enterprise authentication; the service is deliberately a synthetic public demo.
- Active slots and request/body limits reject early without queueing provider work.
  Their storage is bounded; process-local quotas are not a distributed spending cap.
- Only three dependency pins changed: PyJWT `2.13.0 -> 2.15.1`, pypdf
  `6.16.2 -> 6.19.0`, urllib3 `2.7.0 -> 2.8.0`. No advisory was blanket-ignored.

## Contracts later phases must preserve

- `create_deployment_app(settings, runtime_builder=None)` selects private/public mode.
  `create_public_demo_app` revalidates settings and requires an executor whose
  `requires_security_context` is true. Reuse these factories and formal lifespan.
- Public bootstrap: `GET /api/v1/demo/session` returns
  `{"mode":"public_demo","session_ttl_seconds":1800}` with `Cache-Control: no-store`.
  It sets `__Host-nexus-demo`: Secure, HttpOnly, SameSite=strict, Path=/, no Domain.
  A valid cookie is retained without TTL refresh; expired/invalid cookies get a new subject.
- Cookie wire format: `v1.subject.issued.expires.HMAChex`; random 32-byte subject,
  HMAC-SHA256 domain-bound to configured origin. Keep the signing key stable across
  revisions if visitor ownership should survive; key rotation invalidates visitors.
- `POST /api/v1/agent/execute` requires that cookie and exactly one matching `Origin`.
  Absent/null/foreign/duplicate origins are denied. Bootstrap alone allows absent
  Origin for direct clients. Fetch Metadata, when supplied, allows `same-origin`/`none`.
  JSON content type is required; no permissive CORS was introduced.
- Execution body accepts `request_id` (maximum 128 characters), optional `session_id`
  (maximum 128) and `query` (maximum 8000); extra fields are forbidden. Scopes never
  come from client body/headers or forwarded IPs.
- Fixed tenant `nexus-public-demo`, role `public_demo_reader`, principal type `DEMO`,
  authentication `DEMO_COOKIE`, created by `make_demo_principal`.
- Knowledge grants: namespace `enterprise_kb`, documents `DOC-ORG-001`,
  `DOC-AGENT-001`, `DOC-INV-001`. Data grants: domain `enterprise_operations`, read
  resources `products`, `inventory_snapshots`, `purchase_orders`, `suppliers`.
  Preserve downstream column allowlists as well.
- Allowed scenarios `knowledge/data/mixed`; workflows `direct/controlled_mixed`;
  skills `enterprise-knowledge-qa`, `enterprise-data-analysis`, `inventory-risk-diagnosis`;
  tools `run_knowledge_agent`, `run_data_agent`.
- `SessionScope` uses the verified cookie subject and tenant. The executor hashes
  tenant + subject + client session label before memory access. Same label across
  visitors must stay isolated. New Session changes the label, not the visitor identity.
- Default public limits: cookie TTL 1800s, active executions 2, visitor requests 10,
  global requests 60, bootstraps 120 per 60s, visitor counter capacity 1000,
  body size 65536 bytes, body timeout 10s. See `public_demo_*` settings for bounds.
- Errors: 401 `unauthenticated`, 403 `demo_origin_forbidden`, 408 `demo_body_timeout`,
  413 `demo_request_too_large`, 415 `demo_json_required`, 429 `demo_capacity_exceeded`
  with `Retry-After`. Admission slots must release on failure/cancellation/disconnect.

## Environment and execution

Settings use `DECISION_AGENT_` environment variables and `.env` as configured in
`config/settings.py`; `.env.example` is the safe reference. Never log real `.env` values.
`DECISION_AGENT_DEPLOYMENT_MODE=private` is default; invalid explicit modes fail validation.
Public mode requires a canonical HTTPS origin, non-placeholder signing/provider/database
secrets, HTTPS LLM/Milvus endpoints, Milvus token, external database host, corpus root
and enabled controlled workflow. Check the validator before adding Cloud SQL socket
support: public-mode host assumptions will need to remain coherent with the new transport.

Memory defaults to `disabled`; choose `in_memory` explicitly for eventual demo V1.
Redis exists but URLs with embedded credentials are rejected. One Cloud Run instance
does not preserve memory across restarts/revisions or prevent temporary overlap.

Python project minimum is 3.11; validated local environment is CPython 3.11.15 with
Torch `2.13.0+cpu`. Use repo `.venv`, not global Python. The lock is not yet a finalized
production CPU image supply-chain strategy. Model revisions already pinned:

- `BAAI/bge-small-zh-v1.5`: `7999e1d3359715c523056ef9478215996d62a620`.
- `BAAI/bge-reranker-base`: `2cfc18c9415c912f9d8155881c133215df768a70`.

Typical setup from repository root (local validation used the CPU backend):

```bash
uv venv --python 3.11 --managed-python .venv
uv pip install --python .venv/bin/python --torch-backend cpu -r requirements.lock
uv pip install --python .venv/bin/python -e . --no-deps
```

Existing run commands, requiring appropriate configured dependencies/corpus/provider:

```bash
docker compose up -d
.venv/bin/python scripts/initialize_knowledge_corpus.py
.venv/bin/python scripts/run_local_demo.py knowledge
.venv/bin/python scripts/run_local_web_demo.py mixed --port 8000
.venv/bin/python -m uvicorn decision_agent.main:app --host 127.0.0.1 --port 8000
```

Local demo cases are positional `knowledge`, `data`, `mixed`, not `--case` flags.
Ingestion supports `--dataset-root`; otherwise it uses the configured root.
The formal private ASGI app still rejects execution without a trusted resolver.
The local-demo runner intentionally binds loopback and rewrites local demo audit/workflow
configuration. It is not the cloud launcher. A validated `$PORT` launcher is still P2.

Ignored raw evidence is in workspace `.p0-runtime/evidence` and temporary files in
`.p0-runtime/tmp`; repo `.venv`, `.cache` and `.tmp-p*` are local artifacts, not fresh-clone
requirements. Keep pytest temporary/audit paths outside the Git repository but within
the authorized workspace: local-demo path tests require that separation.

## Validation already performed

These are recorded completed checks, not new test executions during this docs-only task.
Exact commands, timestamps, source/log/report hashes and limitations are in
[P1_VALIDATION.json](deployment/P1_VALIDATION.json).

| P1 check | Recorded result |
| --- | --- |
| Unit suite | 1858 passed, zero failures/errors/skips. |
| Offline integration selection | 287 passed, zero failures/errors/skips. |
| New public-demo cases | 52; includes actual executor visitor/session isolation, grants, cookies, origins, quota/body/cancellation behavior. |
| Exact security evaluation | 28/28; no unauthorized release, sensitive leak, provider/tool bypass. |
| Ruff lint/format, JS syntax, Compose config, lock consistency, pip check | Passed. |
| Frozen retrieval v1/v2 evidence and M9 metric derivation | Passed without recomputing models or calling the provider. |
| Resolving and pinned dependency audits | Zero reported vulnerabilities, no ignored advisories. |
| Wheel and installed-package smoke | UI/assets/health 200, unbootstrapped readiness 503; real stdio discovery of six tables, zero SQL queries. |
| Gitleaks staged diff | Zero findings. |

GitHub CI for implementation HEAD was rechecked while preparing this handoff:
[run 37119077485](https://github.com/Akgithub2028/NexusAgent-Enterprise-Autonomous-Multi-Agent-Decision-Intelligence-Platform/actions/runs/37119077485),
all six jobs successful: quality, unit, offline-integration, security-evaluation,
secret-scan, dependency-scan. Test execution is offline; CI dependency installation
and advisory lookup require network access.

P0 recorded 1806 unit, 235 offline and 28 security passes; its failed dependency audit
is retained as historical evidence and superseded by P1 remediation. Do not rewrite it.

Useful regression commands:

```bash
mkdir -p ../.p0-runtime/tmp ../.p0-runtime/evidence
TMPDIR="$PWD/../.p0-runtime/tmp" .venv/bin/python -m pytest -q tests/unit --basetemp ../.p0-runtime/tmp/handoff-unit
TMPDIR="$PWD/../.p0-runtime/tmp" .venv/bin/python -m pytest -q -m offline_integration --strict-markers --import-mode=importlib --basetemp ../.p0-runtime/tmp/handoff-offline
.venv/bin/python scripts/run_security_evaluation.py --output ../.p0-runtime/evidence/security.json
.venv/bin/python scripts/validate_dependency_lock.py
.venv/bin/python -m pip check
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
node --check src/decision_agent/web/app.js
docker compose config --quiet --no-interpolate
.venv/bin/python scripts/verify_retrieval_evidence.py
.venv/bin/python scripts/verify_retrieval_v2_evidence.py
.venv/bin/python -m pip_audit --strict -r requirements.lock
```

## Known limitations and unfinished work

No live LLM calls, real SQL/vector queries, full BGE model loads, cloud provisioning,
public HTTPS checks or cloud load tests were performed for P1. Installed-wheel stdio
discovery is not a real SQL execution test. Existing Starlette/httpx TestClient
deprecation warnings do not fail tests. No other unresolved functional defect is
established by the recorded P1 checks.

Quota storage is bounded but process-local; cookie clearing can reset visitor quota,
although process-wide/bootstrap limits remain. Provider quotas are still required as
an external spending backstop. Memory storage remains unbounded by session count.
Cloud-native mandatory audit, actual JSON log configuration and PORT launch are absent.
Cloud SQL socket transport and managed AUTOINDEX are absent. Serving still provisions
missing vector infrastructure. Upserts alone do not remove obsolete corpus chunks.

Exact next phase: **P2 — Cloud runtime, bounded memory and structured audit**.
Recommended starting point: inspect audit construction in
`application/configured_runtime.py`, governance audit-failure handling in security,
and cleanup in `application/bootstrap.py`/`api/runtime.py`. Define validated file/stdout
audit selection preserving those contracts before wiring the cloud launcher.

P2 TODOs, corresponding to the plan's acceptance criteria:

1. Reuse formal lifespan/AsyncExitStack; preserve unavailable readiness/execution on
   bootstrap failure and deterministic cleanup. Never call `prepare_demo_settings`.
2. Add validated PORT (default 8080), bind `0.0.0.0`, one Uvicorn worker, no reload.
3. Add total-session capacity plus expiry sweeping/eviction. Preserve TTL, max turns,
   deduplication, compaction/version invariants and explicit same-session conflicts.
4. Add file/stdout audit sink selection with closed payload-free events and mandatory
   audit failure behavior. Preserve local fsync, hash-chain anchors and tamper tests.
   Do not claim one global persistent hash chain across cloud instances/revisions.
5. Configure real structured JSON handlers/levels. Keep best-effort trace separate
   from mandatory audit. Include approved release/corpus correlation without queries,
   prompts, outputs, rows, raw visitor identities, cookies, secrets or connection URLs.
6. If adding dependency readiness, use bounded/cached checks and distinguish startup
   status from remote health. Keep liveness independent of remote services.
7. Verify bootstrap/audit failure, cancellation, shutdown/resource cleanup, bounded
   memory and conflict behavior. Document history loss on restart/rollout in the UI/docs.

Remaining phases, not implementations already present:

- **P3:** application Dockerfile/dockerignore; CPU dependency/base/model pins; offline
  reranker controls; corpus manifest; non-root image; neutral-cwd wheel/UI/MCP and
  offline model-load verification.
- **P4:** Cloud SQL socket/config/MCP propagation and pools; explicit synthetic seed
  procedure and database-enforced SELECT on four approved tables; managed AUTOINDEX
  provisioning/validation/search support; serving must fail on missing collections;
  separate ingestion/provisioning permissions; document IAM/secrets/regions/cost inputs.
- **P5:** independent versioned ingestion job using the same release manifest;
  exact counts/IDs, idempotence, obsolete-chunk policy, promotion and rollback.
- **P6:** restricted deployment and real end-to-end queries, HTTPS/cookies, probes,
  startup/load/memory/concurrency/shutdown measurements and provider quotas. Resource
  values in the plan are benchmark candidates, not validated requirements.
- **P7:** GitHub OIDC/Workload Identity Federation and digest-based CD; serialized
  build/ingest/validate/revision/smoke/promotion; public release decision, verified live
  badge, pause and rollback procedures.

Cloud project, budget, regions, Zilliz tier, provider account limits and warm-instance
choice are not resolved. Do not assume cloud credentials or paid resources exist.

## Things the next agent must not accidentally change

- Private fail-closed default, loopback-only local identity and explicit public opt-in.
- Visitor ownership/session hashing, fixed demo grants, origin/cookie/body/admission
  protections, and resource-release behavior. Never use TEST or shared anonymous
  principals for the public runtime or widen grants to all synthetic fixtures.
- SQL AST/column/resource restrictions, provider redaction/governance and mandatory
  audit failure behavior. Database read-only privileges remain an additional boundary.
- MCP stdout protocol, whitelisted child environment and installed-package discovery.
- Local audit integrity/anchors; trace logging must not substitute for mandatory audit.
- Frozen evaluation artifacts, adopted retrieval defaults or benchmark claims. Keep
  the clause-aware alternative separate; fixture business dates/timezone are deliberate,
  not dates to update to the current wall clock.
- Existing model revision pins and async inference locks without evidence for a change.
- Ingestion separation and exact corpus/vector ID checks. Do not ingest on API startup.
- Historical P0 evidence or current P1 evidence merely to make a changed implementation
  appear validated. Refresh directory notes/fingerprints and add new phase evidence.
- Core graphs, UI architecture and internal MCP topology without a phase requirement.
  No separate frontend or public MCP service is needed for the planned deployment.
- Scope boundary: do not implement beyond the phase authorized by the user; never
  add a live badge or describe cloud deployment as completed before actual verification.
