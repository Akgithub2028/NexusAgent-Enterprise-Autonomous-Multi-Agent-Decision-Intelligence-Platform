# P0 repository audit

Reviewed 2026-10-03. Source: `2e2b34c220158c1711409ddb1335fba00fbe375f` on `main`.
The checkout was clean and matched remote `main` before this documentation change.
No applicable `AGENTS.md` was found in the checkout or its workspace ancestor chain.
The repository is already cloned; no second checkout or external file deletion was used.

P0 changes documentation only. Deployment adapters, model downloads, provisioning and
live provider/database tests belong to later phases. See the [plan](IMPLEMENTATION_PLAN.md).

## Runtime and transport

- [`main.py`](../../src/decision_agent/main.py) already provides the production ASGI app.
  It constructs Settings and the configured builder, deferring external initialization
  to the lifespan. `DECISION_AGENT_APP_NAME` is required. There is no public-demo mode.
- [`api/app.py`](../../src/decision_agent/api/app.py) serves `/` and `/assets` from the
  installed package's `web/` directory. No separate frontend host is needed. `/health`
  is process liveness; `/ready` aggregates registered required checks and runtime status.
  An unregistered required dependency is false. Readiness is not an automatic continuous
  ping of every external system.
- [`api/runtime.py`](../../src/decision_agent/api/runtime.py) and
  [`application/bootstrap.py`](../../src/decision_agent/application/bootstrap.py) own
  publication, revocation and AsyncExitStack cleanup. Bootstrap failure leaves API
  execution and readiness unavailable while health/UI can still be served.
- [`application/configured_runtime.py`](../../src/decision_agent/application/configured_runtime.py)
  requires the complete LLM triple, corpus root and read-only database password. Non-test
  execution additionally requires an audit path. It composes the existing router, skills,
  tools, reviewer, memory and governance. MCP startup discovery is exercised, but the
  default builder does not enable the separate database connectivity preflight.
- [`api/models.py`](../../src/decision_agent/api/models.py) accepts request ID, session
  ID and query only, with forbidden extra fields and length caps. Scope is not a client
  request field. [`api/routes.py`](../../src/decision_agent/api/routes.py) obtains trusted
  SecurityContext through an injected resolver before formal execution.

## Identity and memory

[`api/security.py`](../../src/decision_agent/api/security.py) defaults to rejection.
[`demo/web.py`](../../src/decision_agent/demo/web.py) trusts only loopback clients, and
[`run_local_web_demo.py`](../../scripts/run_local_web_demo.py) binds loopback. Binding the
local runner to all interfaces does not make its security adapter suitable for public use.
`prepare_demo_settings()` also forces controlled workflow and an external local audit
path; the cloud factory must not reuse those configuration overrides.

The exact fixture grants in [`demo/local.py`](../../src/decision_agent/demo/local.py) are:

| Demo case | Documents in `enterprise_kb` | Tables in `enterprise_operations` | Workflow / skill |
| --- | --- | --- | --- |
| knowledge | DOC-ORG-001, DOC-AGENT-001 | none | direct / enterprise-knowledge-qa |
| data | none | products, inventory_snapshots | direct / enterprise-data-analysis |
| mixed | DOC-INV-001 | products, inventory_snapshots, purchase_orders, suppliers | controlled_mixed / inventory-risk-diagnosis |

The local tenant/subject/role are `local-demo-tenant`, `local-demo-principal` and
`local_demo_reader`. P1 will use a separate demo tenant and verified per-visitor subjects,
with a proposed union of the above fixed grants. The existing fixture corpus has other
documents and the SQL guard has other tables; those are not automatically public grants.

[`security/models.py`](../../src/decision_agent/security/models.py) enforces immutable
identity/scopes and explicit factories for system/test provenance. There is no anonymous
public-user factory. P1 must specify truthful server-issued identity provenance without
pretending visitors are authenticated human accounts or using test identities.

[`application/executor.py`](../../src/decision_agent/application/executor.py) validates
SessionScope before memory access and derives a scoped key from tenant, subject and the
client session label. Reuse this mechanism; a shared subject would defeat visitor isolation.
[`web/app.js`](../../src/decision_agent/web/app.js) persists a random session label in
localStorage and rotates it on New Session. This label is not proof of visitor identity.
There is currently no signed cookie bootstrap, origin check or public admission limiter.

[`memory/in_memory.py`](../../src/decision_agent/memory/in_memory.py) is locked and checks
optimistic versions, deduplicates turns and bounds per-session history/TTL. It does not cap
the total session dictionary, and expired records are removed on access rather than by a
global sweep. Whole concurrent requests can still conflict on versions. P2 needs bounded
session storage and explicit conflict behavior. Redis is supported but disabled by default;
Settings rejects Redis URLs containing embedded credentials. One Cloud Run instance does
not provide persistent sessions across restarts or overlapping revisions.

## SQL and MCP

[`data/executor.py`](../../src/decision_agent/data/executor.py) builds a lazy SQLAlchemy
`mysql+pymysql` TCP engine with connect timeout and `pool_pre_ping`. There is no Unix socket
setting, TLS connection configuration or explicit pool sizing. SQL execution sets MySQL
MAX_EXECUTION_TIME. The safe-query service also applies a timeout fallback and pool disposal.
Keep these bounds when adding the Cloud SQL transport.

[`data/sql_guard.py`](../../src/decision_agent/data/sql_guard.py) validates SELECT ASTs,
fixed table/column allowlists, row/cell caps and prohibited operations. Its six approved
tables include sales_orders/sales_order_items as well as the four proposed public tables;
the public context is intentionally narrower. Local SQL initialization grants SELECT on
the entire synthetic database. Cloud serving credentials should be narrowed independently
of the application guard. Fixture dates and business definitions use the June 2026 demo
timeline and Asia/Shanghai semantics; preserve those rather than substituting today's date.

[`mcp_client/enterprise_data_client.py`](../../src/decision_agent/mcp_client/enterprise_data_client.py)
starts `sys.executable -m decision_agent.mcp_server` over stdio, discovers tools and closes
the session deterministically. Configured startup opens/closes one discovery session;
data execution owns its own sessions. This is an internal subprocess, not a public remote
MCP service. The child receives a fixed Settings whitelist; a new socket field must be
added there as well as to the parent SQL configuration. Its cwd/PYTHONPATH derive from the
installed module location. P0 wheel smoke verifies discovery in that layout; the container
will still need its own neutral-cwd smoke test.

[`mcp_server/enterprise_data_server.py`](../../src/decision_agent/mcp_server/enterprise_data_server.py)
returns fixed schema/business definitions and lazily opens SQL on query. Consequently,
successful protocol/schema discovery alone does not prove a working MySQL connection.
Use the existing explicit preflight for that release gate. Child stdout is MCP protocol;
JSON diagnostic/audit logging must not corrupt it. The
[`scoped workflow client`](../../src/decision_agent/workflows/data_agent.py) filters exposed
schema and authorizes table access before delegating queries.

## Retrieval, ingestion and model packaging

[`retrieval/factory.py`](../../src/decision_agent/retrieval/factory.py) already separates
`initialize()` (serving, no corpus upserts) from `initialize_for_ingestion()`.
[`retrieval/pipeline.py`](../../src/decision_agent/retrieval/pipeline.py) reads local generated
chunks, initializes both models, checks that Milvus IDs exactly match the local child IDs,
and builds local BM25 and parent expansion. External vector storage does not replace
these local assets. The default corpus contains 12 documents, 36 parents and 101 children.
The clause-aware variant is separate; do not silently change the serving corpus in P0.

[`retrieval/milvus_store.py`](../../src/decision_agent/retrieval/milvus_store.py) supports
URI/token/database configuration but validates HNSW exclusively, including COSINE, schema
version, dimension and construction parameters. Search passes HNSW `ef`. Zilliz's
[AUTOINDEX](https://docs.zilliz.com/docs/autoindex-explained) therefore requires deliberate
adapter changes and live compatibility tests. Also, serving's current store initialization
can create a missing schema/index; split that provisioning permission before assigning
read-only vector credentials.

[`initialize_knowledge_corpus.py`](../../scripts/initialize_knowledge_corpus.py) uses the
formal ingestion runtime, deterministic upserts, count validation and cleanup. Its upserts
do not remove obsolete IDs. New immutable collections, shared corpus manifests and a
validated promotion/rollback pair are the planned release strategy.

Existing Settings already pin model revisions:

| Model | Revision | Serving requirement |
| --- | --- | --- |
| BAAI/bge-small-zh-v1.5 | 7999e1d3359715c523056ef9478215996d62a620 | 512-dimensional CPU embeddings |
| BAAI/bge-reranker-base | 2cfc18c9415c912f9d8155881c133215df768a70 | CPU cross-encoder |

[`retrieval/embeddings.py`](../../src/decision_agent/retrieval/embeddings.py) supports cache
and local-files-only and forbids trust_remote_code. The
[`reranker`](../../src/decision_agent/retrieval/reranking.py) lacks equivalent offline/cache
controls in the configured factory. Both adapters already offload model load/inference
to threads and use inference locks. Full model downloads/loading were not part of P0.

## Audit, infrastructure and CI

[`security/audit.py`](../../src/decision_agent/security/audit.py) uses a closed payload-free
event schema, fsynced JSONL hash chain and external anchor to detect tampering/truncation.
[`security/governance.py`](../../src/decision_agent/security/governance.py) treats mandatory
audit differently from best-effort traces. Replacing its file path with stdout is not a
configuration-only change and must not erase failure/integrity semantics.
[`observability/sinks.py`](../../src/decision_agent/observability/sinks.py) logs JSON at INFO,
but the current main entrypoint does not configure a dedicated JSON handler/level.
OpenTelemetry-compatible vocabulary does not mean an OTel exporter is installed.

[`docker-compose.yml`](../../docker-compose.yml) provisions localhost MySQL 8.4.4, Milvus
2.6.17, etcd and MinIO with persistent volumes. It contains neither the application image
nor Redis. No Dockerfile currently packages serving. Keep Compose as the local environment.
Cloud SQL requires explicit schema/seed administration instead of its local init scripts.

[`pyproject.toml`](../../pyproject.toml) supports Python >=3.11 and uses Hatchling for
`enterprise-decision-agent` 1.0.2. CI uses Python 3.11, despite the root README's Python
3.12 badge. The lock installed successfully in isolated CPython 3.11.15; local validation
selected Torch 2.13.0+cpu. This is a baseline environment choice, not yet a reproducible
production CPU image. P3 must pin that packaging strategy.

[`ci.yml`](../../.github/workflows/ci.yml) defines six checks: quality, unit,
security-evaluation, secret-scan, dependency-scan and offline-integration. It has no release
workflow, WIF, image publication or deployment. Tests use deterministic substitutes;
dependency install/scanning and future image builds still need networking. The current
unit count is 1,806, differing from the README's historical 1,802; the measured result is
recorded without changing frozen benchmark claims.

The networked `pip-audit --strict -r requirements.lock` exited 1: **24 reported advisories**
in PyJWT 2.13.0 (13), pypdf 6.16.2 (8) and urllib3 2.7.0 (3). These are findings in the
unchanged baseline lock, not failures caused by the P0 documentation. The
[advisory inventory](P0_DEPENDENCY_AUDIT.json) records IDs, aliases and suggested fixed
versions. One PyJWT finding has no fix version in this scan. This evidence is not an
exploitability assessment; dependency remediation/review is a mandatory next-phase
public-release gate. P0 does not upgrade the lock or suppress the scan.

All other recorded baseline checks passed, including 1,806 unit tests, 235 offline
integration tests, exact 28-case security assertions, quality/frozen evidence checks,
wheel packaging/stdio smoke and the full 11-commit Git history secret scan. The wheel
smoke emitted an existing Starlette/httpx deprecation warning; this did not fail checks.

## Baseline scope and evidence

See [P0_BASELINE.json](P0_BASELINE.json) for commands, timestamps, exit codes, summaries and
log hashes. Raw logs, JUnit and the wheel remain under the workspace's `.p0-runtime/evidence/`.
The test temp directory is also there because localhost-demo tests intentionally require
their audit root outside the repository. The environment/cache remain ignored in the repo.
No secrets or credential contents are included in the committed evidence.

To reproduce the Python baseline from the repository root, use a separate Python 3.11
environment. With `uv`, the workspace-local setup is:

```bash
mkdir -p .cache/uv .cache/python .cache/python-bin .tmp-p0 ../.p0-runtime/tmp ../.p0-runtime/evidence
export UV_CACHE_DIR="$PWD/.cache/uv"
export UV_PYTHON_INSTALL_DIR="$PWD/.cache/python"
export UV_PYTHON_BIN_DIR="$PWD/.cache/python-bin"
export PIP_CACHE_DIR="$PWD/.cache/pip"
export TMPDIR="$PWD/../.p0-runtime/tmp"
uv venv --python 3.11 --managed-python .venv
uv pip install --python .venv/bin/python --torch-backend cpu -r requirements.lock
uv pip install --python .venv/bin/python -e . --no-deps
export DECISION_AGENT_APP_NAME='Enterprise Decision Agent'
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
```

Then run the commands recorded in P0_BASELINE.json. Resolve `{evidence_dir}` to
`../.p0-runtime/evidence` and `{temp_dir}` to `../.p0-runtime/tmp`. Use fresh owned test
temporary directories, since pytest clears its `--basetemp`. The dependency scan needs
networking and is expected to fail against the unremediated source lock.

### Installed wheel smoke

The additional P0 smoke used a wheel installed into a separate target and asserted its
import origin. This equivalent recipe uses no deployment adapter or live SQL:

```bash
uv build --wheel --out-dir ../.p0-runtime/evidence/dist
uv pip install --python .venv/bin/python --target ../.p0-runtime/wheel-site --no-deps \
  ../.p0-runtime/evidence/dist/enterprise_decision_agent-1.0.2-py3-none-any.whl
export PYTHONPATH="$PWD/../.p0-runtime/wheel-site"
p0_python="$PWD/.venv/bin/python"
cd ../.p0-runtime
"$p0_python" - <<'PY'
import asyncio
from pathlib import Path
import decision_agent
from fastapi.testclient import TestClient
from decision_agent.api.app import create_app
from decision_agent.config import Settings
from decision_agent.mcp_client.enterprise_data_client import EnterpriseDataMCPClient

assert (Path.cwd() / "wheel-site").resolve() in Path(decision_agent.__file__).resolve().parents
settings = Settings(_env_file=None, app_name="P0 wheel smoke", environment="test")
with TestClient(create_app(settings, runtime_readiness_required=True)) as client:
    for route in ("/", "/assets/app.js", "/assets/styles.css", "/health"):
        assert client.get(route).status_code == 200
    assert client.get("/ready").status_code == 503

async def check_stdio():
    async with EnterpriseDataMCPClient.from_settings(settings) as client:
        assert len((await client.get_enterprise_schema()).tables) == 6
        assert (await client.get_business_definitions()).definitions

asyncio.run(check_stdio())
print("Installed wheel UI, readiness and stdio smoke passed")
PY
```

Offline tests and frozen verification do not prove live LLM, SQL, Zilliz, full BGE model,
container startup or cloud IAM behavior. Those remain explicit P3–P7 gates. The dependency
audit is networked; it is recorded separately from the offline test contract.

## Completion checklist

- [x] Locate existing checkout; record source commit, clean state and remote agreement.
- [x] Inspect applicable instructions, packaging, lock, Compose, CI and tests.
- [x] Trace formal lifecycle, default-deny API, local-only identity and UI transport.
- [x] Identify exact demo grants and existing tenant/subject session hashing.
- [x] Trace SQL transport, guard, read-only initialization and stdio child configuration.
- [x] Trace serving/ingestion split, local corpus dependency and HNSW compatibility gap.
- [x] Inspect model pin/offline settings, audit integrity and actual logging setup.
- [x] Run and record the available baseline checks and their limitations.
- [x] Build/check the wheel, UI assets and real stdio discovery without external data I/O.
- [x] Prepare P1–P7 with source seams, prerequisites and acceptance gates.
- [x] Add directory navigation, maintained READMEs and source fingerprints.
- [x] Verify documentation links, source fingerprints and docs-only diff before delivery.

P0 completion means the repository baseline and implementation boundary are established.
It does not mean the application is ready for public deployment. P1 has not started.
