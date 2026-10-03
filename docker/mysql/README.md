# Local MySQL bootstrap

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: supporting inventory / contracts.

Entry files: [init/01-schema.sql](init/01-schema.sql), [init/02-seed.sql](init/02-seed.sql), [init/03-create-readonly-user.sh](init/03-create-readonly-user.sh).

Entrypoint scripts run for local initialization, not automatically in Cloud SQL. Keep seed/admin credentials out of serving.

Validation and phase gates: [deployment plan](../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../docs/deployment/DIRECTORY_INDEX.md).
