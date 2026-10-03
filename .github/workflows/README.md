# Continuous integration workflows

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: supporting inventory / contracts.

Entry files: [ci.yml](ci.yml).

Keep credential-free PR checks. P7 adds immutable image releases and scoped OIDC deployment.

Validation and phase gates: [deployment plan](../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../docs/deployment/DIRECTORY_INDEX.md).

release.yml checks exact-commit CI, serializes releases, builds immutable images and runs explicit candidate/public/rollback/pause operations behind protected OIDC environment. ci.yml is unchanged.
