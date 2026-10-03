# Codex implementation handoff

Updated 2026-10-03 during P6, based on P5 commit
`267e8f4859445f86faadc55a45eb1cc768b09be1`. Inspect Git for the final phase commit.

## Objective and phase status

Deploy the existing evidence-grounded multi-agent backend and Workbench as one CPU
Cloud Run container, with synthetic MySQL in Cloud SQL and vectors in Zilliz. Separate
versioned ingestion from serving; use scoped secrets, cloud logs and eventually OIDC CD.

P0 audit/documentation, P1 public-demo isolation/admission, P2 cloud runtime/audit/memory,
and P3 reproducible image are implemented and validated. P4 adapters and Terraform are
implemented; Zilliz and local socket/SQL privilege checks passed. The owner explicitly
authorized placeholder billing configuration because billing setup is blocked. Actual
Google provisioning/Cloud SQL validation and vector reader separation are deferred gates.
P5 ingestion/promotion implementation is ready; managed first/repeat execution remains
deferred. P6 restricted deployment/measurement tooling is implemented; managed deployment and
measurements remain blocked. P7 CD/live badge is unstarted.
P3/P4 implementation is complete under that adjusted scope; deployment acceptance
is not complete until the deferred managed gates pass.

Authoritative contracts/evidence: [phase plan](deployment/IMPLEMENTATION_PLAN.md),
[P1](deployment/P1_PUBLIC_DEMO.md), [P2](deployment/P2_CLOUD_RUNTIME.md),
[P3/P4 report](deployment/P3_P4_IMPLEMENTATION.md),
[P3/P4 evidence](deployment/P3_P4_VALIDATION.json),
[operator runbook](../deploy/cloud-run/README.md).

## Checkout and authorization

Repository is the `NexusAgent-Enterprise-Autonomous-Multi-Agent-Decision-Intelligence-Platform`
child of `/media/aayaann-kausar/New Volume1/Project Enhancements-Deployements`. Set workdir
explicitly. Work only within this workspace; do not delete unrelated/outside files.
Branch main. User authorizes commit/push and has authorized P6 implementation. P0/P1/P2 historical commits
are in prior evidence/Git. Existing gh authentication works; no PAT is needed in commands.
No applicable AGENTS.md was found; no subagents were requested.

Never commit supplied credentials. The owner-created Zilliz credential file is ignored
both locally and in `.gitignore`. `.cache`, `.tmp-*`, Terraform state/plans/inputs and
cloud CLI config are ignored. Keep the provided Groq credential out of documents/Git.

## Current architecture and important contracts

FastAPI serves `/` and `/assets` itself. Formal lifespan/AsyncExitStack builds scoped
request execution, memory and LangGraph knowledge/data/mixed paths, then reviewer and
cited answers. Internal installed-module stdio MCP owns guarded MySQL access. Child
stdout is protocol only; diagnostics stay stderr. `/health` is liveness; `/ready` is
bootstrap/registered checks, not continuous remote health.

Knowledge uses CPU BGE embedding, Milvus, local BM25/RRF/parents and BGE reranking.
The corpus remains 12 documents, 36 parents, 101 children. Local/remote IDs must agree
exactly. Serving now calls `initialize_reader()` (validate existing schema/index only,
no create/load/index/upsert/delete); ingestion explicitly owns the writer initialization.
AUTOINDEX gets empty creation/search parameters; local HNSW keeps M16/efConstruction200/ef64.
Both require COSINE/512 and the existing versioned metadata/schema/filter validation.

SQL supports TCP locally or validated `/cloudsql/project:region:instance` Unix sockets.
Socket overrides host/port and is explicitly passed through the MCP whitelist. Pool size
2/zero overflow, bounded checkout/connect/read/write waits, recycle1800 and +08:00 session
timezone are configured. SQLGlot guard, row/cell limits and disposal remain intact.
Admin seed is independent of serving. The public SQL account receives SELECT on four
approved tables only; independent driver checks prove denied writes/out-of-scope reads.

P1 fixed public tenant/grants remain unchanged. Cookies are signed opaque distinct visitor
identities with Secure/HttpOnly/SameSite=strict; execution needs exact configured HTTPS
Origin and cookie. Session labels are hashed with verified tenant/visitor. Private mode
still fails closed, and local-demo remains loopback-only. No public credentials/scopes
come from the client. Process admission quotas are not provider spending caps.

P2 stdout audit remains mandatory and fail closed on write/flush/release failure. Closed
payload-free JSON events have per-process chains; flush is not durable cloud delivery.
Local file chains/anchors remain intact. Memory is ephemeral, bounded1000sessions with TTL,
turn limits, deduplication and optimistic conflicts. Live history is never evicted for a
new visitor. UI warns about restart/expiry history loss; Redis remains deferred.

## P3/P4 files and purposes

- Dockerfile/.dockerignore: digest-pinned Python3.11.14/bookworm amd64, non-root UID10001,
  wheel/UI, immutable corpus/models, P2 cloud launcher; context allowlist excludes secrets.
- `deploy/cloud-run/requirements-runtime.lock`: 94 hashed runtime-only Linux CPython3.11
  wheels; direct CPU Torch URL. Build lock separately has five hash-pinned build tools.
- `scripts/prepare_cloud_release.py`: verifies pinned MIT snapshots, hashes all assets,
  generates manifest and corpus/collection release ID.
- `src/decision_agent/release.py`: pre-resource manifest/config/hash validation; wired into
  configured runtime through optional release_manifest_path (set by image).
- Reranker/settings/factory: cache and local-only options; remote code always disabled.
- Data executor/settings/MCP whitelist: Cloud SQL socket and bounded transport/pool settings.
- Milvus store/factory: AUTOINDEX and explicit serving-reader lifecycle.
- Terraform main/provider lock: Artifact Registry, separate serving/ingestion identities,
  SQL/database, per-secret access, SQL client IAM and project budget alerts. No secret values,
  SQL admin account provisioning, public service, ingestion job or CD in Terraform.
- Admin SQL seed/verify and disposable managed vector-check scripts; targeted regression
  tests. Updated directory notes, deployment status/evidence and this handoff.

The baked corpus ID is `m2c1_9e02a989eace4274`; collection
`nexus_m2c1_9e02a989eace4274`. Docker ENV defaults must change with a new corpus manifest.
Embedding pin: BAAI/bge-small-zh-v1.5 /7999e1d3359715c523056ef9478215996d62a620.
Reranker pin: BAAI/bge-reranker-base /2cfc18c9415c912f9d8155881c133215df768a70.
Models are local at /opt/release/models/{embedding,reranker}; HF access is disabled in
runtime. Inference/load already use asyncio.to_thread and per-model locks.

## Operator state and exact unfinished work

- Confirmed project `nexus-agent-510512`; Google region `us-west1`; Zilliz region gcp-us-west1.
  Endpoint is recorded in the ignored-safe runtime example. Cluster is serverless/free.
- Groq endpoint https://api.groq.com/openai/v1; requested model openai/gpt-oss-20b was present
  in authenticated models response200. No completion or end-to-end agent call was made.
- Owner requested a small budget and ONE warm instance. Agent selected $50/month alert
  target, subject to billing currency conversion and account pricing. This is not a cap.
  Cloud Run max1/concurrency2/2CPU/4GiB are candidate P6 values, not cloud benchmarks.
- Google Cloud CLI541.0.0 is installed under `.cache/cloud-sdk/google-cloud-sdk`; account
  login/ADC completed successfully in this workspace. Credentials/config remain under
  `.cache/cloud-sdk/config`, not Git. Terraform1.13.3 binary is ignored `.tmp-p34/terraform`.
- Actual project inspection returned billingEnabled=false and no linked billing account.
  The logged-in account's available billing account list was empty. No paid infrastructure
  was provisioned. Owner reported billing setup issues and authorized dummy configuration/offline planning.

Deferred deployment prerequisites: recheck billing, inspect account currency/budgets/quotas, finalize costs,
apply validated Terraform, create/admin-seed SQL, validate real Cloud SQL through MCP,
create scoped vector credentials (tier-dependent, do not assume cluster RBAC on Free),
load Secret Manager values through stdin and record numeric versions. Serving must never
receive admin/write credentials. Verify provider-enforced denied vector mutations.
Then update evidence/handoff with real managed results. P6 is the next implementation phase if authorized. Actual P5 job execution/promotion
awaits those prerequisites.

## Run/verify commands and results

```bash
.venv/bin/python scripts/run_local_web_demo.py
.venv/bin/python -m decision_agent.cloud
docker build --platform linux/amd64 -t nexusagent:p34 .
docker run --rm --network none --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m --memory 4g --cpus 2 \
  --workdir /tmp --entrypoint python nexusagent:p34 /opt/validate_cloud_image.py
```

The cloud launcher requires real runtime secrets/config/index to become ready.
Local smoke intentionally proved unconfigured ready503, UI/assets/health200 and SIGTERM0.
Offline image/model/MCP smoke passed in20.202s at peak1,295,292KiB RSS, CPU-onlyTorch2.13.0,
512-dimensional normalized vectors and finite rerank score, UID10001/no network.
Image size approximately2.87GB. This is not a Cloud Run startup or concurrency benchmark.

Focused tests227passed plus config/launcher/ingestion90passed. Ruff lint/format, lock
consistency and pip check passed. Terraform init/fmt/validate passed. Real local socket
MCP preflight/rawSELECT passed; MySQL independently denied UPDATE/DELETE/INSERT and
out-of-scope SELECT. Real Zilliz create/insert/exact-ID/filter checks and confirmed cleanup
passed. Zilliz drop RPC may time out after success; verifier accepts only confirmed absence.
Raw logs are ignored `.tmp-p34`; portable committed evidence is authoritative in fresh clones.
P2's broader baseline was1897unit/322offline/28security and all six CI jobs green.

For cloud commands in this checkout:

```bash
export CLOUDSDK_CONFIG="$PWD/.cache/cloud-sdk/config"
export CLOUDSDK_PYTHON="$PWD/.venv/bin/python"
export GOOGLE_APPLICATION_CREDENTIALS="$CLOUDSDK_CONFIG/application_default_credentials.json"
.cache/cloud-sdk/google-cloud-sdk/bin/gcloud billing projects describe nexus-agent-510512
.tmp-p34/terraform -chdir=deploy/cloud-run validate
```

## Do not accidentally change

Preserve formal lifecycle/rollback, private deny defaults, loopback local adapter, fixed
public scopes/visitor ownership/CSRF, mandatory audit failure semantics, payload-free logs,
MCP whitelist/protocol stdout, SQL guard/limits and fixture business dates. Do not mutate
frozen retrieval/evaluation assets. Do not silently introduce live ingestion/provisioning
at API startup. Do not widen vector/SQL credentials for public serving. Keep model revisions,
512 normalized COSINE vectors, schema/filter checks and image/corpus/collection pairing.
Do not treat local socket tests as real Cloud SQL evidence or mark billing/provisioning
complete without successful managed checks. No live badge or deployment URL exists yet.

## P5 additions (2026-10-03)

`ingestion/cloud_job.py` is an explicit installed-module job, never API startup. Reuses
formal ingestion and immutable manifest verification. Cloud Storage generation-zero
create locks serialize writers across executions; generation-specific deletion and
manual stopped-execution recovery prevent expired leases permitting overlapping writes.
Permanent collection bindings reject changed manifests, including partial first runs.
Exact IDs/canonical fields and a filtered hybrid retrieval sample precede cleanup and
a payload-free immutable receipt. Published reruns use reader mode with no upserts.

Terraform adds private/versioned `project-nexus-releases` metadata bucket and scoped
ingestion object access; serving receives no bucket permissions. Minimum Terraform is
1.7 for existing mock tests. `scripts/prepare_corpus_promotion.py` requires an actual
successful execution and receipt matching the digest/manifest, then emits a descriptor
only. P6 owns restricted revision/traffic operations. See P5 runbook for job commands,
lock recovery, promotion and rollback. No new dependencies or source-corpus edits.

New P5 images must be built: retained `nexusagent:p34` lacks the job module. Managed
execution, interrupted-job recovery and actual traffic rollback remain untested gates.
Do not expire locks automatically, repurpose collections, promote from receipts alone,
or delete retained rollback image/config/collection pairs.

P5 checks: 108 targeted tests passed; Ruff passed. Terraform validate and two mock
plans passed. Installed wheel includes the job module. No real cloud job ran.

Code-only images reuse a validated corpus through reader revalidation and separate
`images/<SHA256(image-reference)>.json` receipts. The original corpus receipt and
rollback pair remain unchanged. Promotion requires the matching image receipt.

## P6 additions (2026-10-03)

Total API cooperative execution deadline240s (configurable downward), safe504,
executor cancellation and admission release precede transport300s. Model calls
now hold thread locks inside to_thread so cancellation does not permit overlapping
CPU calls; native work already running cannot be forcibly stopped. No provider,
SQL guard, scope, audit, memory or frozen fixture contract was relaxed.

`scripts/deploy_restricted_revision.py` plans by default; apply revalidates billing,
P5 execution/receipt, private IAM, exact p6 tag origin and prior pinned secrets.
Bootstrap creates only an absent deny-all private service to obtain the real tag
URL. Candidate deploy saves prior service/IAM without overwriting, moves no traffic,
uses four numeric reader secrets, serving identity, SQL socket,2CPU/4GiB/concurrency2,
min1/max1 and HTTP300s. Startup/readiness use ready; liveness uses health. SDK541
lacks readiness-probe: update the workspace-local SDK before managed application.

`scripts/measure_restricted_service.py` checks IAM, secure cookies, scoped routes,
M9 cases, memory isolation, two concurrent requests, wrong-Origin denial and health
latency. It reports payload-free small-sample p50/p95, not cold-start or memory.
Token files/output stay ignored. No live LLM request or Cloud Run resource was
created: authenticated billing recheck still false. Follow P6 runbook's exact gates
for cold/warm startup, memory, SQL denials, reconnects, SIGTERM, restart/overlap,
cloud audit review and actual rollback/pause. P6 managed acceptance is incomplete.
P7 implementation may follow only when authorized; public release needs all gates.

P6 local verification:112 focused tests passed, Ruff/format/lock checks passed.
Current wheel over retained P3/P4 image passed real offline CPU512embedding/reranking
and installed MCP smoke (24.286s,1,291,956KiB RSS,UID10001,SQL0). This is not a P6
image digest or a cloud cold-start/memory measurement. Dry bootstrap/candidate plans
used explicitly fake receipts/digest and contacted no cloud APIs.
