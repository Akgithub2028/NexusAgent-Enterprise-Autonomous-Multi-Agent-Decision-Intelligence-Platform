# P3/P4 implementation and evidence

Implemented on 2026-10-03 from P2 commit `a7f4d5dcdde2bffaecd95340a63f41689e35c111`.
P3 and P4 implementation are complete under the owner's adjusted scope. Billing is
blocked; the owner explicitly authorized dummy configuration and continuing implementation.
Actual Google provisioning and provider-enforced vector reader separation are deferred
deployment gates, not claimed as completed.
The owner confirmed project `nexus-agent-510512`, region `us-west1`, Zilliz serverless
in `gcp-us-west1`, and Groq model `openai/gpt-oss-20b`.

## What changed

- `Dockerfile` / `.dockerignore`: digest-pinned Python 3.11 amd64, 94 hashed CPU runtime
  wheels, five separately hashed build tools, installed wheel/UI, pinned local models,
  synthetic corpus, non-root execution and the P2 cloud launcher. Build context is an
  allowlist; credentials, caches, Git, audit and evaluation artifacts stay outside.
- `scripts/prepare_cloud_release.py`: pinned upstream license/revision verification,
  immutable source/model hashes and release manifest, 12 documents/36 parents/101 children.
- `release.py`: verifies release hashes, offline paths/revisions, vector schema/dimension,
  metric, collection and corpus ID before configured-runtime resource initialization.
- Reranker settings/factory: explicit cache/local-only options; remote model code disabled.
- `data/executor.py`, settings and MCP whitelist: validated Cloud SQL Unix sockets with
  TCP fallback, bounded pools/driver waits, session timezone and existing cleanup/deadlines.
- `milvus_store.py` / factory: AUTOINDEX support with provider-specific empty parameters,
  existing HNSW validation retained; serving uses a reader-only lifecycle and refuses
  provision/load/upsert/delete. Explicit ingestion retains the writer lifecycle.
- `deploy/cloud-run`: pinned Terraform provider/lock, registry, two runtime identities,
  SQL instance/database, scoped secrets/IAM and project billing alerts; operator inputs
  and runtime configuration examples. No secret values or public service are Terraform inputs.
- Admin seed/reader verification and isolated managed-vector verification scripts; focused
  regression tests for the new contracts. See [operator runbook](../../deploy/cloud-run/README.md).

## Checks performed

Machine-readable evidence: [P3_P4_VALIDATION.json](P3_P4_VALIDATION.json).

| Check | Result |
| --- | --- |
| Focused retrieval/runtime/data/MCP tests | 227 passed |
| Settings/cloud launcher/ingestion contract tests | 90 passed |
| Ruff lint/format, development lock consistency and pip check | Passed |
| Docker image build from allowlisted context | Passed; approximately 2.87 GB |
| Image offline model/UI-package/stdio MCP smoke | Passed with network disabled, neutral cwd, UID 10001, read-only root, 256 MiB tmpfs, 4 GiB/2 CPU limits |
| Actual BGE embedding | 512 dimensions, unit norm |
| Actual BGE reranking | Finite score; both models loaded offline |
| Combined offline smoke resource measurement | 20.202 seconds; peak RSS 1,295,292 KiB (about 1.25 GiB) |
| Container HTTP UI/assets/health | 200; unconfigured readiness 503; SIGTERM exit 0 |
| Real local MySQL socket/MCP child | Connection preflight and raw SELECT passed; owned pool closed |
| MySQL privilege check independent of SQLGlot | Four approved table reads; UPDATE/DELETE/INSERT and out-of-scope SELECT denied |
| Real Zilliz serverless | AUTOINDEX/COSINE/512 creation, three exact IDs, two document-filtered hits, confirmed disposable collection removal |
| Groq supplied credential/model availability | Authenticated models request 200; requested model present; no completion generated |
| Terraform 1.13.3 + Google provider 6.50.0 | Init/format/schema validation and mock-provider plan assertions passed |

The SQL socket check used a real local MySQL 8.4 container with the identical socket
transport/installed MCP process, not a provisioned Cloud SQL instance. It does not prove
Cloud SQL IAM/proxy connectivity. The image HTTP smoke intentionally had no external
runtime secrets/index; fail-closed readiness was the expected result. A configured ready
cloud revision, full agent/provider flow and cloud cold-start/load measurements remain P6.
The image/model smoke is not a concurrency benchmark or Cloud Run startup guarantee.

Zilliz's deletion RPC timed out while deletion completed. The helper now independently
checks absence after any deletion timeout, and reports success only after cleanup is
confirmed. Disposable collections from earlier attempts were also confirmed absent.
The supplied test credential permitted provisioning; least-privilege serving credentials
have not been established. Do not inject that writer/admin credential into a public service.

## Deferred managed deployment gates

1. Google Cloud CLI/ADC login completed. Project inspection confirms billingEnabled=false
   and no available billing accounts. The owner authorized explicit dummy billing inputs and offline planning; actual billing
   must be linked before any real apply. CLI/config stay under ignored `.cache/cloud-sdk`.
2. Inspect project billing account, existing budget and resources; use the selected small $50/month alert target (convert to billing currency). The owner
   confirmed region us-west1 and one warm instance. The dummy account ID is
   `000000-000000-000000`; it must never be used for real provisioning.
3. Estimate costs for SQL/disk/backups, vector tier, request/warm compute, registry/build,
   logs, provider and egress using account/region pricing. Do not imply alerts cap spending.
4. Review/apply Terraform; initialize fresh SQL with admin-only seed; verify DB privileges
   again on actual Cloud SQL, then prove its socket connectivity through the MCP child.
5. Create separate vector read/write identities according to tier RBAC, validate TLS and
   any allowlisting, upload secrets to Secret Manager and record numeric secret versions.
   Prove the serving provider identity independently cannot create/insert/delete.
6. Record cloud resource identifiers and actual managed results in evidence/handoff.

P5 is the next implementation phase: versioned ingestion job and promotion/rollback.
Its real execution requires the deferred managed prerequisites. No serving corpus ingestion or public Cloud Run deployment was done.
P6 deploys and measures the restricted service; P7 adds CD/live badge.

## External contracts checked

Cloud SQL attachment exposes `/cloudsql/INSTANCE_CONNECTION_NAME`; serving needs SQL
client IAM as well as its restricted DB account. [Google connection documentation](https://docs.cloud.google.com/sql/docs/mysql/connect-run).
Zilliz uses AUTOINDEX; HNSW construction/search options must not be forwarded.
[Zilliz index API](https://docs.zilliz.com/reference/python/python/Management-add_index).
Groq's OpenAI-compatible endpoint and model capabilities are documented by
[Groq](https://console.groq.com/docs/model/openai/gpt-oss-20b); per-account quotas must be
checked rather than inferred from [published plan examples](https://console.groq.com/docs/rate-limits).
