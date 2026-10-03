# Deterministic external-I/O substitutes

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: supporting inventory / contracts.

Entry files: [enterprise_data_mcp_stub_server.py](enterprise_data_mcp_stub_server.py).

Fixtures validate protocol and control flow without provider/database access. Do not report substitute-backed tests as real managed-service validation.

Validation and phase gates: [deployment plan](../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../docs/deployment/DIRECTORY_INDEX.md).
