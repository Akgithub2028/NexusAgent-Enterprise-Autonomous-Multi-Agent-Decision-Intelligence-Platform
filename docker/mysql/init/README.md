# Local schema, seed and read-only user initialization

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: supporting inventory / contracts.

Entry files: [01-schema.sql](01-schema.sql), [02-seed.sql](02-seed.sql), [03-create-readonly-user.sh](03-create-readonly-user.sh).

Local user has SELECT over the synthetic database. P4 narrows cloud table grants and verifies actual write denial. Shell files must retain LF/POSIX text.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
