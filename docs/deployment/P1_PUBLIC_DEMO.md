# P1 public-demo boundary

Implemented on 2026-10-03 from P0 commit `635a8ecc697754d798376626b0380f06d60e4cbf`.
This phase adds opt-in identity, scopes and admission to the existing formal runtime.
It does not provision cloud resources or implement P2's launcher/audit/memory changes.
[Measured validation](P1_VALIDATION.json) records the completed local checks.

## Entry and configuration

[`decision_agent.main:app`](../../src/decision_agent/main.py) now selects the deployment
factory. `DECISION_AGENT_DEPLOYMENT_MODE=private` is the default and keeps the rejecting
API resolver. Unknown modes or invalid public settings fail validation. The existing
localhost demo retains its loopback-only resolver and local audit settings.

`public_demo` requires all of the following, without placeholder values:

- A canonical external HTTPS `DECISION_AGENT_PUBLIC_DEMO_ORIGIN`, such as the eventual
  Cloud Run origin, without a path, trailing slash, user information or explicit port 443.
- An independent `DECISION_AGENT_PUBLIC_DEMO_SIGNING_SECRET`, generated with
  `secrets.token_urlsafe(32)` and supplied through Secret Manager in the eventual release.
  Keep the same secret across revisions; changing it invalidates all current visitors.
  Character-length/variation checks reject obvious mistakes but cannot measure entropy.
- A complete LLM triple, HTTPS provider and vector endpoints, vector token, explicit
  external database host, read-only DB password and knowledge dataset root.
- `DECISION_AGENT_CONTROLLED_WORKFLOW_ENABLED=true` for the reviewed mixed workflow.

The [.env example](../../.env.example) lists every new setting and remains private by
default. Public settings do not override audit paths or silently enable workflows.
Non-test configured runtime still requires its existing audit sink. Cloud SQL Unix-socket
support, managed AUTOINDEX and stdout audit remain later phases, so this is not yet a
Cloud Run deployment recipe.

## Visitor and API contract

Before executing, request `GET /api/v1/demo/session` from the configured origin. It sets
`__Host-nexus-demo` with Secure, HttpOnly, SameSite=Strict, Path=/ and no Domain attribute.
Responses are `Cache-Control: no-store`. A valid cookie is preserved rather than rotating
identity or extending its absolute lifetime; a missing/invalid/expired cookie creates a
new visitor. The response contains demo mode and configured lifetime, not the cookie.

Cookie format is versioned and strictly bounded, with a random 256-bit subject, issuance,
expiry and HMAC-SHA256. The signed input is domain-separated and bound to the configured
origin. Verification enforces signature, version, subject shape, TTL and expiry. It has
no client-selected algorithm or capability claims and does not use JWT.

Execution requires the cookie, JSON content type and an exact `Origin` header matching
configuration. Duplicate, absent, null or foreign origins fail. Cross-site/same-site
Fetch Metadata is rejected when supplied. CORS is not enabled. These origin checks
protect browser requests from CSRF; they are not proof of enterprise authentication.
Direct API clients use the same cookie jar and send the configured Origin:

```bash
# Run from the repository, after a future service has a verified URL.
# Keep the cookie jar ignored and delete only your own jar when finished.
demo_origin='https://YOUR_VERIFIED_SERVICE_ORIGIN'
mkdir -p .tmp-p1
curl --fail --cookie-jar .tmp-p1/visitor.cookies "$demo_origin/api/v1/demo/session"
curl --fail --cookie .tmp-p1/visitor.cookies \
  --header "Origin: $demo_origin" --header 'Content-Type: application/json' \
  --data '{"request_id":"demo-request-1","session_id":"demo-session-1","query":"What is the synthetic enterprise demo scope?"}' \
  "$demo_origin/api/v1/agent/execute"
```

The Workbench bootstraps before sending each query, preserves its random session label
and New Session behavior, and handles 429/401 errors. On private/local apps the bootstrap
endpoint returns 404, so the existing execution contract remains usable.

## Fixed grants and ownership

The resolver creates an explicit `demo` / `demo_cookie` principal through a dedicated
factory. It is a server-verified synthetic visitor, not an authenticated employee or a
test principal. Tenant is `nexus-public-demo`; role is `public_demo_reader`.

| Grant | Fixed value |
| --- | --- |
| Knowledge namespace | enterprise_kb |
| Documents | DOC-ORG-001, DOC-AGENT-001, DOC-INV-001 |
| Data domain | enterprise_operations |
| Tables | products, inventory_snapshots, purchase_orders, suppliers |
| Query capability | read |
| Scenarios | knowledge, data, mixed |
| Workflows | direct, controlled_mixed |
| Skills | enterprise-knowledge-qa, enterprise-data-analysis, inventory-risk-diagnosis |
| Tools | run_knowledge_agent, run_data_agent |

Client identity/scope/forwarded-IP headers cannot modify these grants, and additional
scope fields in the request body remain forbidden. Existing scoped retrieval, MCP schema
filtering, SQLGlot column/table checks, read-only SQL and evidence review remain in place.

SessionScope uses the signed visitor subject. The actual formal executor derives memory
keys from tenant, subject and session label. Two visitors choosing the same label access
different histories. Changing a label creates a new history within the same visitor;
knowing another visitor's label does not grant their history. A stolen valid cookie is
a bearer credential for that demo visitor, so cookies are never logged or returned in
response bodies. History remains ephemeral and a renewed visitor cannot recover prior
ownership after expiry. P2 will bound the memory store itself and document rollout loss.

## Admission and limits

[`api/public_demo.py`](../../src/decision_agent/api/public_demo.py) installs a guard even
before request-model parsing/execution. The public factory also refuses a runtime without
formal authorization enabled. Admission uses a lock for atomic process-local counters
and non-waiting active slots. Overload returns stable `demo_capacity_exceeded` / HTTP 429
with Retry-After; rejected requests perform no provider/tool execution.

| Setting suffix (`DECISION_AGENT_`) | Default | Meaning |
| --- | --- | --- |
| PUBLIC_DEMO_MAX_ACTIVE | 2 | Simultaneous admitted requests, including body reads |
| PUBLIC_DEMO_REQUESTS_PER_VISITOR | 10 | Admitted requests per visitor window |
| PUBLIC_DEMO_REQUESTS_GLOBAL | 60 | Admitted requests per process window |
| PUBLIC_DEMO_BOOTSTRAPS_GLOBAL | 120 | Bootstrap requests per process window |
| PUBLIC_DEMO_WINDOW_SECONDS | 60 | Fixed-window duration |
| PUBLIC_DEMO_MAX_VISITORS | 1000 | Maximum live rate-counter entries |
| PUBLIC_DEMO_MAX_BODY_BYTES | 65536 | Total request bytes, including streamed bodies |
| PUBLIC_DEMO_BODY_TIMEOUT_SECONDS | 10 | Total body-read deadline |
| PUBLIC_DEMO_COOKIE_TTL_SECONDS | 1800 | Absolute visitor cookie lifetime |

Expired counter entries are pruned; live entries are not evicted to reset quotas. A
full counter map rejects new visitors until expiry. Slots release on cancellation,
body disconnect/timeout/size rejection and execution failure. Existing query (8000),
request ID (128) and session ID (128) limits still apply. Body-size caps also constrain
JSON encoding overhead. Success and failure execution responses are non-cacheable.

Clearing cookies can obtain a new visitor and reset that visitor's quota; it cannot reset
the process-global execution quota or bootstrap quota. These are process-local abuse
controls, not a distributed global budget. Overlapping instances/revisions have separate
counters. Provider-side quotas and an operator pause procedure remain public-release
requirements. To pause execution, deploy `private` mode or remove service traffic;
existing demo cookies do not grant access in private mode.

## Dependency remediation

The lock now selects PyJWT 2.15.1, pypdf 6.19.0 and urllib3 2.8.0. Compatible minimum
constraints prevent returning below these versions on regeneration. Other pins were
preserved. Both the complete resolving audit and the pinned-package audit report zero
known vulnerabilities, without ignored IDs or skipped affected packages.

The [PyJWT options-mutation advisory](https://github.com/jpadilla/pyjwt/security/advisories/GHSA-gvp8-978c-rx2q)
still lists no patched version but identifies its affected range through 2.13.0. The
selected [2.15.1 release](https://github.com/jpadilla/pyjwt/releases/tag/2.15.1) is outside
that range, and a regression test confirms caller options are not mutated. No application
authentication relies on JWT. Historical P0 findings remain preserved as source evidence.

## Completion evidence and remaining gates

The new offline tests cover default denial, invalid config, forged principal construction,
tampered/expired/origin-bound cookies, spoofed grants, table denial before MCP execution,
same-label visitor isolation through the actual executor, New Session, origin/Fetch
Metadata checks, rate/global/map/active bounds, streamed body limits/timeouts, cancellation
and failure cleanup, and the PyJWT regression. Existing unit/offline/security/frozen
checks and package/stdio smoke remain regression gates.

P1 is complete when [P1_VALIDATION.json](P1_VALIDATION.json) records these outcomes and
the maintained directory fingerprints match. No live LLM, cloud IAM, managed database,
full BGE loading or public HTTPS deployment claim is made by these offline checks.
P2 has not started.
