# P6 restricted deployment and measurements

P6 implementation is ready; managed acceptance is **blocked**, not completed.
On 2026-10-03 the authenticated project check again returned `billingEnabled=false`
and no linked account. No Cloud Run revision, paid infrastructure or live LLM calls
were created. P4 provisioning/scoped secrets and P5 successful managed ingestion must
precede real P6 execution. P7 remains unstarted.

## Implemented boundaries

Every API execution has a configurable cooperative deadline (default/maximum240s).
The public body budget is10s; Cloud Run transport is300s. Expiration returns a safe
504 `execution_deadline_exceeded`, cancels the formal executor and releases admission.
Dependency TimeoutError remains500 rather than being mistaken for this deadline.
Existing cancellation/audit/memory semantics remain intact. A running native CPU or
blocking driver call cannot be forcibly killed by asyncio cancellation: driver waits
remain bounded, and model thread locks now survive cancellation of their awaiters.
This prevents overlapping calls into one model after timeout. Do not claim that
provider work already sent or native inference is instantly stopped.

`scripts/deploy_restricted_revision.py` renders JSON environment and an argument-array
command by default. `--apply` rechecks billing, the real successful P5 execution and
image receipt, then refuses public IAM bindings, disabled invoker checks, mismatched
bootstrap tag origins or plaintext secrets in the rollback snapshot. It saves the
previous service/config/IAM before deployment and refuses to overwrite that snapshot.
The operator must use a new ignored output directory for every deployment attempt.
It never changes traffic or grants public invocation. Deploy only to this owned,
restricted demo service; P7 will own releases of a publicly accessible service.

The command pins the same manifest/digest/collection and four numeric reader secret
versions, uses the serving identity/SQL socket, one worker, gen2,2CPU/4GiB,concurrency2,
HTTP300s and service-level min1/max1. Revision min0/max1 avoids separately warming all
retained revisions. Tagged candidates and temporary revision overlap can still have
additional instances; these settings are not a strict fleet/cost ceiling.

Startup `/ready` allows48x5s=240s; liveness `/health` runs every10s; native readiness
`/ready` runs every10s. These are candidate settings, not cloud measurements. The
installed workspace SDK541 lacks `--readiness-probe`; apply checks help and fails
before mutation until an SDK exposing that flag is available. Current official
Cloud Run documentation supports it. `/ready` represents bootstrap/registered checks,
not continuous SQL/provider availability. Successful API probes remain necessary.

## First private bootstrap and candidate

After billing/P4/P5 acceptance, push a new image containing P6 and ingest/revalidate
that exact digest. Recreate the P5 promotion descriptor for its successful execution.
Do not use the retained P3/P4 image or a locally fabricated receipt.

For a service that does not yet exist, use the tool's `--bootstrap` mode, which
rechecks billing/P5 evidence and refuses to change an existing service. It deploys
a **private-mode** bootstrap with IAM required, the validated digest, serving
identity, the same numeric secrets/SQL/resource/probe settings, and the `p6` tag.
No public-demo origin is needed: the security resolver denies every execution.
Initial traffic goes only to this deny-all service. The mode records that no prior
service existed and saves the generated service status; it never replaces an
existing service's traffic.

```bash
.venv/bin/python scripts/deploy_restricted_revision.py \
  --config .tmp-p6/config.json --promotion .tmp-p6/promotion.json \
  --output .tmp-p6/bootstrap-01 --bootstrap
# Review plan, then repeat with --apply; real numeric versions/digest are required.
```

Obtain the exact `p6` URL from service status (not the canonical service URL):

```bash
gcloud run services describe nexusagent --project nexus-agent-510512 --region us-west1 \
  --format=json > .tmp-p6/service.json # select the traffic entry whose tag is p6
```

Copy `restricted.config.example.json` into an ignored `.tmp-p6` directory; fill the
actual tag origin and numeric secret versions. Keep provider writer/admin credentials
out. Use the current P5 promotion descriptor:

```bash
.venv/bin/python scripts/deploy_restricted_revision.py \
  --config .tmp-p6/config.json --promotion .tmp-p6/promotion.json \
  --output .tmp-p6/candidate-01
# Review candidate-01/plan.json and runtime.env.json, then:
.venv/bin/python scripts/deploy_restricted_revision.py \
  --config .tmp-p6/config.json --promotion .tmp-p6/promotion.json \
  --output .tmp-p6/candidate-01 --apply
```

P6's `public_demo` application mode is behind Cloud Run IAM. The app still requires
its signed visitor cookie and exact tag Origin. Only an authorized tester gets
`roles/run.invoker`; never bind allUsers/allAuthenticatedUsers or disable IAM checks.
For an interactive browser, use an authenticated forwarding setup that preserves
HTTPS host/Origin/cookies; a localhost proxy does not establish those acceptance
properties. The scripted authenticated HTTPS client checks the actual tag URL.

## Measurements and acceptance

Generate an ID token for an authorized invoker, with the canonical service URL as
audience even when requesting a tag. Use service-account impersonation if necessary;
store the token only in an ignored0600 file. Do not print it in terminal logs. Tokens
are short-lived. Client requests use X-Serverless-Authorization for Cloud Run IAM;
application authorization remains the cookie. The measurement script never writes
tokens, cookies, queries or answers to its result.

```bash
.venv/bin/python scripts/measure_restricted_service.py --origin ACTUAL_P6_TAG_ORIGIN \
  --token-file .tmp-p6/id-token --repeats 2 > .tmp-p6/https-measurements.json
```

This issues at most14agent calls with repeats3 (four cases x3 plus a concurrent pair),
uses isolated visitors, and checks knowledge/data/mixed and insufficient evidence
against existing frozen M9 contract fields. It samples p50/p95, secure cookies,
multi-turn memory, distinct visitor ownership, wrong-Origin denial and health during
sequential inference. It refuses an unauthenticated200 and missing citations. Sample
sizes2–3 are smoke estimates, not statistically stable production percentiles.
Health is checked separately from the pair because two transport slots are occupied.

**Exact remaining gates:**

- P4 real SQL SELECT-only denials through the attached IAM socket/MCP, scoped vector
  mutation denials and network/TLS checks; P5 first/repeat successful executions.
- Actual startup timing and240s probe headroom, from creation to ready for a NEW instance;
  first request latency is not cold-start latency with min1. Record image/revision.
- Cloud/container memory peak over startup and concurrent knowledge/mixed workloads;
  do not substitute P3 model RSS or mocked HTTP timings. Keep4GiB/2CPU until measured.
- Authenticated HTTPS measurement output, real grounded facts/citation inspection,
  health p95 under sequential inference, concurrent-pair latency and quota behavior.
- Independently deny SQL UPDATE/DELETE/INSERT/out-of-scope SELECT with the public SQL
  identity. A planner refusing a malicious prompt is not proof of database permissions.
- Restart/overlap: same visitor+label after a process restart gives empty history;
  old and new revisions have independent ephemeral memory. Do not promise affinity.
- Dependency interruption/reconnect: stop/recover only disposable test infrastructure;
  check unavailable responses, driver reconnection and reader collection behavior.
- SIGTERM during idle and in-flight work: capture exit/cleanup duration under10s and
  audit outcomes. Inspect Cloud Logging payload-free schemas and missing/sink failure
  behavior; do not claim stdout flush is durable cloud delivery.
- Exercise return to the retained revision/image/config/secret/collection pair and
  pause recovery. Record actual results before changing P6 status to complete.

## Rollback and pause

Inspect `previous-service.json` (0600) for the prior traffic revision(s) and numeric
secret references. Never delete the retained image, collection or secret versions.
Restore traffic only to a known healthy pinned revision; rollback requires no ingestion:

```bash
gcloud run services update-traffic nexusagent --project nexus-agent-510512 \
  --region us-west1 --to-revisions KNOWN_PREVIOUS_REVISION=100
```

For an IAM-restricted pause, revoke tester invocation and remove the candidate tag
(after saving status). Restore service min0 if no warm instance is desired during the
pause; inspect revision minima too. For an application pause, deploy the same image
in private mode behind IAM with the same dependencies, then route to that deny-all
revision. Neither min0 nor removal of a traffic tag alone blocks the canonical URL.
Do not delete the entire service as a routine rollback. Public release is P7.

References: [Cloud Run probes](https://docs.cloud.google.com/run/docs/configuring/healthchecks),
[timeout semantics](https://docs.cloud.google.com/run/docs/configuring/request-timeout),
[tagged URL authentication](https://docs.cloud.google.com/run/docs/authenticating/service-to-service),
[deployment flags](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy).
