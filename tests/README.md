# Deterministic regression and opt-in live tests

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: supporting inventory / contracts.

Entry files: [unit/public_release/test_shell_line_endings.py](unit/public_release/test_shell_line_endings.py), [fixtures/enterprise_data_mcp_stub_server.py](fixtures/enterprise_data_mcp_stub_server.py).

P0 records 1,806 unit and 235 offline integration passes. Live external-service tests are separate gates, not implied by offline success.

Validation and phase gates: [deployment plan](../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../docs/deployment/DIRECTORY_INDEX.md).
