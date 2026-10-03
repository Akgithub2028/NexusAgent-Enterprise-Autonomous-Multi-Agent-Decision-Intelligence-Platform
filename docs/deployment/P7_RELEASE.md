# P7 CI/CD and public release

Implementation prepared 2026-10-04. **Live deployment remains blocked** by disabled
billing and unfinished P4/P5/P6 managed acceptance. No live URL/badge, cloud OIDC pool
or paid resource was created. `LIVE_ACCEPTANCE.json` deliberately records false gates.
The existing six-job CI workflow is unchanged.

## Implemented release sequence

`release.yml` defaults disabled and serializes all operations without cancelling a
running release. A successful main-branch CI run triggers only a **candidate**; manual
dispatch supports candidate/public/rollback/pause. Every action checks the original
six green CI jobs for its exact source commit before cloud authentication. The job
requires protected `nexus-release` environment approval and OIDC—no SA key or PAT.
Pinned third-party action commit SHAs were resolved from the official repositories.

Candidate order: exact-commit checks → Docker/model build → registry image digest →
explicit one-task writer job → real P5 execution/receipt verification → restricted
preview revision → authenticated HTTPS measurement → immutable candidate metadata.
The same digest serves and ingests. Published corpus reruns validate without writes;
code-only images get their own validation receipt. A new corpus gets a new collection.
CI never creates services, seeds SQL or provisions a missing corpus during API startup.

Public order: explicit dispatch + environment approval → immutable candidate metadata
and matching reader config → approved managed acceptance for that image → recheck real
ingestion receipt → save previous service/IAM → deploy production tag without traffic
→ authenticated health/UI/cookie/knowledge smoke → 100% traffic → public invoker binding
→ unauthenticated HTTPS verification → immutable public receipt. Failed verification
after traffic promotion attempts rollback to the saved traffic and previous public
binding. A provider/IAM outage may also break rollback; inspect the saved snapshots.

## Preview separation and resource scope

`nexusagent-preview` stays IAM-restricted. `nexusagent` becomes public only after the
explicit public action. A Cloud Run tag shares service IAM, so a tag on an already
public production service cannot replace the restricted preview boundary. Production
tag checks still exercise exact canonical Origin/cookies before traffic moves.
The preview temporarily warms for checks; scale it to minimum 0 when testing ends. Production
uses the owner's minimum 1 preference. Overlap and tagged revisions may temporarily add
instances; maximum 1 is not an absolute cost/fleet ceiling.

The separate `deploy/github-oidc` Terraform root grants targeted registry/service/job,
SA attachment and metadata bucket permissions. Numeric repository/owner IDs, main,
exact workflow path and environment subject constrain federation. Project roles are
read-only; production administration is bound only to that service. The release SA
has no direct Secret Manager accessor. See its README for the trusted-code limitation.

## GitHub configuration completed in this checkout

The repository previously had no environments or Nexus release variables. Created:

- `nexus-release`, with the repository owner as required reviewer, admin bypass disabled,
  and deployment branch policy permitting only `main` branches, not tags.
- `NEXUS_RELEASE_ENABLED=false` as a repository variable.

Self-review is allowed so the single repository owner can approve their own release;
add another reviewer and disable self-review if the project gains maintainers. This
approval is a release decision, not proof that acceptance measurements happened.
Cloud identity/config variables remain unset until real infrastructure exists.

## Exact activation prerequisites

1. Link real billing, confirm currency/costs/$50 alert plan, apply P4 infrastructure and
   prove SQL/socket/MCP and provider-enforced vector permissions with reader credentials.
2. Execute P5 first/repeat ingestion of the actual immutable image. Preserve model/
   corpus/collection and numeric secrets for rollback. Recover stale writer locks only
   after independently confirming their execution stopped.
3. Follow P6 bootstrap for **both** owned services, with deny-all private mode first.
   Then establish the restricted preview's actual `p6` origin and canonical audience;
   retain the production canonical origin. Use an SDK with native readiness probe flags.
4. Apply reviewed `deploy/github-oidc` Terraform after the services/job exist. Verify
   a real short-lived GitHub exchange and the resource-scoped permissions. No placeholders
   may enter a real apply or release.
5. Fill `release.config.example.json` with actual URLs and numeric versions. Set these
   nonsecret GitHub variables: `NEXUS_CONFIG_JSON`, `NEXUS_WIF_PROVIDER`,
   `NEXUS_RELEASE_SERVICE_ACCOUNT`. Config variables must never contain API keys or passwords.
6. Enable repository `NEXUS_RELEASE_ENABLED=true` only when candidate prerequisites pass.
   Approve the protected environment. A candidate run writes its proof under
   `gs://<bucket>/candidates/<SHA256(image-reference)>/<run-id>.json`.
7. Complete every gate in `LIVE_ACCEPTANCE.json` with real measurements/evidence for
   that digest. Commit the reviewed record with status `approved`, exact image, all 12 gates
   true and nonempty evidence links. Cold start/RSS/driver permissions cannot be inferred
   from the small HTTPS sample. Wait for exact-commit CI to pass.
8. Dispatch `public` with the digest reference and successful candidate run ID. Approve
   the environment only after reviewing the candidate/config/evidence and rollback path.

The release workflow never self-approves and never fabricates acceptance. Automatic
candidates still require environment approval. There is no deployment on PRs/forks.
The job's 55-minute timeout may need adjustment after real cold-start/latency measurements.

## Commands

```bash
# All references are actual values, never example/dummy billing IDs.
gh workflow run release.yml --ref main -f action=candidate
gh workflow run release.yml --ref main -f action=public \
  -f image=REGISTRY_APP_AT_SHA256 -f candidate_run=SUCCESSFUL_CANDIDATE_RUN
gh workflow run release.yml --ref main -f action=rollback -f rollback_run=PUBLIC_OR_PAUSE_RUN
gh workflow run release.yml --ref main -f action=pause
```

Equivalent operator runner: `python -m scripts.run_cloud_release ...`, with the same
configuration, `NEXUS_RELEASE_ENABLED=true`, numeric `GITHUB_RUN_ID`, `RELEASE_SHA` and
an authorized short-lived release identity. Work only from the repository root.
Main-branch workflow dispatch and OIDC provide the release authority in normal use.
The disabled workflow is not an emergency control plane: use the P6 operator runbook
if CI, GitHub approval or federation is unavailable.

## Rollback, pause and recovery

Immutable `rollbacks/<run-id>/{service,iam}.json` preserve prior traffic/config and
public binding state. Rollback restores exact revision percentages and the previous
allUsers invoker state; it does not re-ingest, rebuild or guess secret values. Keep
those revisions, image digests, secret versions and collections through the rollback
window. It does not modify unrelated IAM bindings. Snapshot writes reject plaintext
secrets and floating versions in known runtime secret fields.

Pause saves the same metadata, revokes public invocation, creates a private deny-all
revision, routes to it, clears tags and sets service minimum 0. In-flight/native operations
may still finish; minimum 0 alone never means “API disabled.” Restoring a pause uses its
saved run ID. Restore the selected warm minimum explicitly if required. Inspect
revision minima and provider spending independently. Interrupted ingestion jobs may
leave a generation lock: use P5's stopped-execution recovery procedure.

## Verified live badge

Only after a public receipt, correct current traffic revision and real unauthenticated
Workbench/assets/health/readiness checks:

```bash
python scripts/add_live_demo_badge.py --config .tmp-release/config.json --run-id ACTUAL_PUBLIC_RUN
```

Review/commit/push the README change and update its deployment status/ledger with the
verified receipt and real URL. The helper writes only the badge placeholder; it does
not falsely mark other acceptance stages complete. No fake URL or static “live” badge
is present in this implementation. Public UI must keep its synthetic-scope and
restart/expiry memory notices.

## Validation and remaining gates

Actionlint, Ruff, focused release/rollback/acceptance tests, Terraform validation/mock
plan, frozen retrieval verifier, Markdown link/fingerprint checks and exact-commit CI
verify implementation. Required real gates remain billing/provisioning, scoped OIDC,
managed ingestion, P6 measurements, HTTPS public Workbench and actual rollback/pause.
Do not mark P7 live acceptance complete until those recorded operations pass.

References: [Google federation pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines),
[GitHub environment controls](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments),
[Google auth action](https://github.com/google-github-actions/auth).

Candidate runs attempt to reset the preview service to minimum 0 after restricted
deployment or measurement failure. Production retains minimum 1. If provider errors
prevent cleanup, inspect the preview with the P6 operator pause procedure.

OAuth access tokens are explicitly 1 hour, with fresh OIDC authentication after image
build before the long release operation. HTTPS identity tokens are refreshed through
self-impersonation and cached for at most 120 seconds in the measurement runner, so repeated
long requests do not depend on one expiring ID token. Tokens remain memory/environment
only and are never stored in metadata or README.
