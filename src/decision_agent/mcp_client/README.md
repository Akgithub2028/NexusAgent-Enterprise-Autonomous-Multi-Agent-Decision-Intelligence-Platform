# Owned stdio subprocess transport

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: runtime boundary traced.

Entry files: [enterprise_data_client.py](enterprise_data_client.py), [contracts.py](contracts.py).

P4 must propagate socket settings through the fixed child whitelist. Keep subprocess cleanup, bounded errors and installed-package discovery working.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
