# Cloud Run infrastructure and operator boundary

P3 image and P4 adapters/infrastructure implementation are complete. The owner deferred
real provisioning because billing setup is blocked and authorized dummy/offline configuration.
Google Cloud provisioning requires an
authenticated account, billing account and explicit budget. Project is
`nexus-agent-510512`; Google/Zilliz region `us-west1` is confirmed. Zilliz is serverless;
Groq model `openai/gpt-oss-20b` is available under the supplied credential.
No secret value belongs in this directory or Terraform state.

## Build and validate P3

```bash
docker build --platform linux/amd64 -t nexusagent:p34 .
docker run --rm --network none --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m --memory 4g --cpus 2 \
  --workdir /tmp --entrypoint python nexusagent:p34 /opt/validate_cloud_image.py
```

The image runs UID/GID 10001, one formal cloud worker, and includes the wheel/UI,
CPU-only Torch and pinned MIT BGE snapshots. Build tooling stays in the build stage.
`requirements-runtime.lock` covers 94 runtime packages, with one reviewed amd64/CPython
3.11 wheel hash each. Torch uses an explicit CPU wheel URL; PyPI uses an explicit index.
`requirements-build.lock` separately pins/hashes five wheel-build packages. These locks
are platform-specific and supplement the development `requirements.lock`.
When dependencies change, regenerate their transitive runtime closure with extras and
markers, review against the development lock, hash actual wheels and rerun pip check.
Never include CUDA packages or use `--trusted-host`/disabled TLS.

`prepare_cloud_release.py` verifies upstream pinned commit/license metadata and preserves
model README license notices. It copies 12 synthetic documents and 36 parent/101 child
records, records all asset SHA256 values, and derives a corpus/collection ID from the
corpus hashes. The current image defaults to `nexus_m2c1_9e02a989eace4274` and
`m2c1_9e02a989eace4274`. After corpus changes, update the Dockerfile defaults to the
new manifest ID in the same release; never switch only the remote collection.
The final image build also compares the generated manifest to committed
`corpus-release.json`, rejecting unexpected model or corpus bytes. `release.py` validates
hashes/config before opening serving resources. Both BGE models
load directly from `/opt/release/models` with local-only loading and HF offline flags.
Release verification hashes approximately 1.2 GB at startup; measure real cold starts in P6.

## Review dummy infrastructure without cloud access

```bash
terraform -chdir=deploy/cloud-run init -backend=false
terraform -chdir=deploy/cloud-run validate
terraform -chdir=deploy/cloud-run test
```

The mock-provider plan uses dummy billing account `000000-000000-000000` and checks
secret isolation, SQL protection/encoding and the budget. It provisions nothing.
Never use that dummy ID with a real plan/apply.

## Provision after billing is resolved

```bash
gcloud auth login --update-adc
gcloud config set project nexus-agent-510512
cd deploy/cloud-run
cp operator.auto.tfvars.example operator.auto.tfvars
# Replace dummy billing_account_id; verify amount/currency; region is confirmed.
terraform init
terraform validate
terraform plan -out=provision.tfplan
terraform apply provision.tfplan
```

The pinned Google provider and committed `.terraform.lock.hcl` create Artifact Registry,
separate serving/ingestion identities, MySQL 8.0 with UTF-8 collation and +08:00 timezone,
SQL client permission for serving, five secret containers and per-secret grants, and
project-scoped monthly alerts. Terraform does not create secret values, SQL users,
public Cloud Run services, ingestion jobs or CI/CD. SQL has no authorized public networks;
use the authenticated Cloud SQL proxy/Cloud Run attachment. Deletion protection is enabled.
The proposed shared-core SQL tier is for a demo; availability/performance are not benchmarked.
Disk is capped at 10 GB with automatic growth disabled. Budget alerts do not stop spending.
Keep state private; a remote backend can be configured before collaborative use.
The selected alert target is $50/month (convert to billing currency); the owner chose one
warm instance for P6. Request-based idle costs alone at 2 CPU/4 GiB are about $39.42 over
730 hours before discounts/free tiers, so a warm demo is not a zero-cost deployment.
[Cloud Run pricing](https://cloud.google.com/run/pricing).

Create secret versions through stdin or console, record each numeric version for deployment,
and never use floating `latest` in release configurations. Serving receives the Groq key,
demo signing key, SQL reader password and vector read token. Ingestion receives only its
vector write token. Admin DB/vector credentials must not enter the serving image/environment.
The supplied Zilliz credential was used for an isolated connectivity test, not a public
serving identity. Check the chosen tier's role availability and create a collection-scoped
read role (describe/query/search/index discovery) and separate provisioning/upsert role.
Application reader checks are additional protection, not a substitute for provider RBAC.

## Seed and independently verify SQL permissions

Create/reset the Cloud SQL root password through the console or an interactive CLI prompt.
Run Cloud SQL Auth Proxy with a local `/cloudsql` socket, or mount its socket into the
image. Supply passwords through environment/secret mounts, never CLI arguments:

```bash
read -rs NEXUS_SQL_ADMIN_PASSWORD; export NEXUS_SQL_ADMIN_PASSWORD
read -rs NEXUS_SQL_READER_PASSWORD; export NEXUS_SQL_READER_PASSWORD
python scripts/manage_cloud_sql_demo.py seed \
  --socket /cloudsql/nexus-agent-510512:us-west1:nexus-demo-mysql
python scripts/manage_cloud_sql_demo.py verify \
  --socket /cloudsql/nexus-agent-510512:us-west1:nexus-demo-mysql
unset NEXUS_SQL_ADMIN_PASSWORD NEXUS_SQL_READER_PASSWORD
```

Seed is explicitly one-time against a fresh database; SQL DDL is not transactional. A
partial admin seed requires inspection/recovery and must not be automatically rerun.
It uses existing schema/fixtures, creates `decision_agent_readonly`, and grants SELECT
only on products/inventory_snapshots/purchase_orders/suppliers. Verify performs SELECTs
and zero-row UPDATE/DELETE/INSERT plus denied sales_orders SELECT directly through MySQL,
independently of SQLGlot. It fails on broader privileges. Keep the fixture dates unchanged.

`DECISION_AGENT_DB_UNIX_SOCKET` accepts only `/cloudsql/project:region:instance`, within
Unix socket path limits. It overrides TCP host/port and propagates only through the MCP
whitelist. Default pool size is 2 with zero overflow, bounded checkout/connect/read/write
waits and 1800-second recycle. Session timezone is +08:00. Local TCP remains supported.

## Validate managed vectors

Set URI, `DECISION_AGENT_MILVUS_WRITE_TOKEN` and `DECISION_AGENT_MILVUS_TOKEN` privately,
then run `python scripts/verify_managed_vector.py`. It owns a randomly named disposable
collection, creates AUTOINDEX/COSINE/512 schema, writes three synthetic records, verifies
exact IDs plus document filters, and confirms collection deletion before reporting success.
Zilliz deletion may complete despite a timed-out RPC; only confirmed absence is accepted.
It does not populate or promote the serving collection (P5).

The formal runtime uses `initialize_reader()`: collection/schema/index validation only,
no create/index/load/upsert/delete. A missing or incompatible collection fails bootstrap.
The ingestion owner retains explicit provisioning through `initialize()` and
`initialize_for_ingestion()`. HNSW retains its parameters; AUTOINDEX gets no HNSW parameters.
Metadata restrictions and exact local/remote chunk-ID agreement remain unchanged.

See [phase report](../../docs/deployment/P3_P4_IMPLEMENTATION.md) for evidence and remaining gates.

## P5 ingestion and release gates

See [P5 runbook](../../docs/deployment/P5_INGESTION.md). The image now includes the
independent ingestion module. Terraform adds a private versioned metadata bucket
and bucket-scoped ingestion object access; serving gets no storage role. Deploy a
single-task job by immutable image digest, with only the numeric vector-write
secret version. Promote only after the successful execution and receipt agree.

## P6 restricted serving

See [P6 runbook](../../docs/deployment/P6_RESTRICTED_DEPLOYMENT.md) for guarded private
bootstrap/candidate commands, exact HTTPS tag origin, four pinned reader secrets,
startup/readiness/liveness probes, measurements and rollback/pause. Cloud acceptance
remains blocked by billing; no live URL exists.

P7 uses a separate restricted preview and production service. release.config.example.json holds nonsecret URLs/numeric secret references only. See ../../docs/deployment/P7_RELEASE.md before activating.
