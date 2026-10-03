# Deterministic regression and opt-in live tests

Reviewed on 2026-10-03 for P2, based on `5ce044b2dfec6b40dd2a7cc05401017975dc062d`; current source fingerprints are recorded below.
Review depth: supporting inventory / contracts.

Entry files: [unit/public_release/test_shell_line_endings.py](unit/public_release/test_shell_line_endings.py), [fixtures/enterprise_data_mcp_stub_server.py](fixtures/enterprise_data_mcp_stub_server.py).

P2 adds launcher/SIGTERM, safe logging, stdout audit failure/release and capacity coverage. Final unit/offline/security results are recorded in P2_VALIDATION.json.

Validation and phase gates: [deployment plan](../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../docs/deployment/DIRECTORY_INDEX.md).
