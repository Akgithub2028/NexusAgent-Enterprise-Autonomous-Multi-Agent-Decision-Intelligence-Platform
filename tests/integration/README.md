# Integration tests with explicit offline/live markers

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: supporting inventory / contracts.

Entry files: [.gitkeep](.gitkeep), [test_bge_reranker.py](test_bge_reranker.py), [test_data_agent_mysql_integration.py](test_data_agent_mysql_integration.py).

The offline_integration marker selects 235 deterministic tests. Live dependencies must be provisioned explicitly; collection alone is not a live test.

Validation and phase gates: [deployment plan](../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../docs/deployment/DIRECTORY_INDEX.md).
