# Internal enterprise-data stdio server

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: runtime boundary traced.

Entry files: [__main__.py](__main__.py), [enterprise_data_server.py](enterprise_data_server.py).

Stdout is protocol-only. Schema discovery is lazy and does not prove SQL connectivity; use explicit database preflight.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
