# Read-only SQL validation and execution

Reviewed on 2026-10-03 for P3/P4, based on `a7f4d5dcdde2bffaecd95340a63f41689e35c111`.
Review depth: runtime boundary traced.

Entry files: [executor.py](executor.py), [sql_guard.py](sql_guard.py), [safe_query_service.py](safe_query_service.py).

P4 SQLAlchemy transport accepts a validated Cloud SQL Unix socket or existing TCP, with bounded pool/driver waits and +08:00 session timezone. SQLGlot, result limits and disposal remain. Admin seed is separate.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
