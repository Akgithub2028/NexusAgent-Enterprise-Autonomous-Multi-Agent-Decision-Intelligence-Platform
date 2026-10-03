# Read-only SQL validation and execution

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: runtime boundary traced.

Entry files: [executor.py](executor.py), [sql_guard.py](sql_guard.py), [safe_query_service.py](safe_query_service.py).

P4 adds socket transport/pool bounds while retaining AST allowlists, SELECT-only execution, timeouts and result caps.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
