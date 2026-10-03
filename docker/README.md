# Local infrastructure initialization assets

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: supporting inventory / contracts.

Entry files: [mysql/init/01-schema.sql](mysql/init/01-schema.sql), [mysql/init/02-seed.sql](mysql/init/02-seed.sql), [mysql/init/03-create-readonly-user.sh](mysql/init/03-create-readonly-user.sh).

Root Compose starts MySQL/Milvus dependencies only. P3 adds an app image; P4 adapts SQL initialization for managed infrastructure.

Validation and phase gates: [deployment plan](../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../docs/deployment/DIRECTORY_INDEX.md).
