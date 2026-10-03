# P5 independent versioned ingestion

Implementation is ready for managed execution. Billing, real P4 infrastructure,
Secret Manager versions and scoped vector credentials remain deferred. No managed
corpus was ingested or promoted during this phase. P6 deployment is unstarted.

## Contracts

The SAME immutable image digest runs `python -m decision_agent.ingestion.cloud_job`
and serving. No LLM, SQL, public-demo cookie or signing secret is needed by the job.
Its only secret is `DECISION_AGENT_MILVUS_TOKEN`, mapped to a numeric version of
`nexus-vector-write-token`. Immutable asset checks run before external resources.
The existing formal `initialize_for_ingestion()` owns embedding/upserts; the local
initializer remains available unchanged.

Cloud Storage control objects use generation preconditions, not process locks.
`locks/<collection>.json` is create-only; only its acquired generation is deleted.
A second execution fails before opening vector resources. Locks have no automatic
expiry: after interruption, confirm the execution and all its tasks have stopped,
inspect the lock's generation, then delete that generation conditionally. Never
blindly delete a lock or retry while the first writer might still be running.

`bindings/<collection>.json` permanently binds a collection to its manifest hash,
including model assets. Even a failed first run cannot repurpose that collection for
a different manifest. A changed corpus must generate a new release and collection;
never delete obsolete rows from an active release to simulate a new version.

Validation compares exact IDs and every canonical non-vector field (including
content, parent, document/version, metadata and schema), then exercises filtered
embedding/vector/BM25/reranking/parent retrieval without an LLM. Runtime cleanup must
succeed before publishing `validated/<collection>.json`. Receipts contain counts,
manifest SHA256, corpus/collection and image digest, without document/query payloads.
A repeat of a published release uses reader initialization and performs no upserts.
A different digest cannot silently replace the validated pair. Failed partial runs
may retry the SAME manifest; exact-ID validation refuses stale/extra records.

Receipts alone do not authorize promotion: the promotion helper also requires a
successful single-task Cloud Run execution for that exact image. This blocks a
receipt left behind when lock release fails. Receipts are operational evidence,
not cryptographic attestations against a compromised ingestion identity.

## Deploy and execute after the P4 gates

Build/push a new P5 image and record its digest; the old P3/P4 image lacks this module.
Fill `ingestion.env.example`, retaining all baked corpus/model configuration.
Copy it to an ignored `ingestion.env.yaml` with real digest/bucket settings. Ensure
this file matches the image passed below. These commands require real infrastructure;
placeholder billing and digest values cannot execute them.

```bash
export PROJECT=nexus-agent-510512 REGION=us-west1
export IMAGE='us-west1-docker.pkg.dev/nexus-agent-510512/nexusagent/app@sha256:REAL_DIGEST'
export WRITE_VERSION=1 # replace with the actual numeric Secret Manager version

gcloud run jobs deploy nexus-ingestion --project "$PROJECT" --region "$REGION" \
  --image "$IMAGE" --service-account "nexus-ingestion@$PROJECT.iam.gserviceaccount.com" \
  --command python --args=-m,decision_agent.ingestion.cloud_job \
  --tasks 1 --parallelism 1 --max-retries 0 --task-timeout 900s \
  --cpu 2 --memory 4Gi --env-vars-file deploy/cloud-run/ingestion.env.yaml \
  --set-secrets "DECISION_AGENT_MILVUS_TOKEN=nexus-vector-write-token:$WRITE_VERSION"
gcloud run jobs execute nexus-ingestion --project "$PROJECT" --region "$REGION" --wait
```

Record the execution name. Run it twice: first writes/validates, second validates
without mutation. Keep task stdout completion metadata and successful execution
status. Terraform provides a private, versioned control bucket; serving receives
no bucket role. Operators preparing promotions need bucket read and execution read
permissions, not the ingestion secret. Confirm provider-enforced reader/write
separation before P6 public access.

```bash
python scripts/prepare_corpus_promotion.py --project "$PROJECT" --region "$REGION" \
  --execution ACTUAL_EXECUTION_NAME --bucket "$PROJECT-nexus-releases" \
  --image "$IMAGE" --manifest deploy/cloud-run/corpus-release.json > .tmp-p5/promotion.json
```

The helper fails closed if the receipt or successful execution differs. It only
prepares a descriptor; P6 must deploy a restricted revision from that digest,
collection and release ID, verify readiness, and then perform traffic promotion.
Before promotion export the previous serving revision/config (including numeric
secret versions, digest and collection), keep its collection/image, and save the
validated descriptor. Roll back traffic to that retained revision; no re-ingestion
is needed. Do not delete old collections until their rollback window closes.

## Verification and remaining acceptance

Targeted tests cover first/repeat runs, validation and cleanup failures, competing
writers, receipt mismatch, digest/execution gates and canonical metadata checks.
Existing Milvus/immutable-release regressions also run. Terraform validate and
mock-provider plan pass. Real cloud first/repeat jobs, interruption recovery,
changed-corpus ingestion and traffic rollback must be measured after billing/P4
provisioning; offline tests are not evidence of those managed outcomes.

References: [Storage generation preconditions](https://docs.cloud.google.com/storage/docs/request-preconditions),
[Cloud Run job deployment flags](https://docs.cloud.google.com/sdk/gcloud/reference/run/jobs/deploy).
