# GitHub automation

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: supporting inventory / contracts.

Entry files: [workflows/ci.yml](workflows/ci.yml).

Six CI checks validate the source. P7 adds image builds and release automation; cloud federation and live deployment await managed acceptance.

Validation and phase gates: [deployment plan](../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../docs/deployment/DIRECTORY_INDEX.md).

P7 adds a disabled-by-default OIDC release workflow. Preserve six CI gates; protected environment/release enablement and real acceptance control live operations.
