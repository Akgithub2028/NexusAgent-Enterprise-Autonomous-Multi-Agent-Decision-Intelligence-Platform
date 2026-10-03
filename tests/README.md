# Deterministic regression and opt-in live tests

Reviewed on 2026-10-03 for P1, based on `635a8ecc697754d798376626b0380f06d60e4cbf`; current source fingerprints are recorded below.
Review depth: supporting inventory / contracts.

Entry files: [unit/public_release/test_shell_line_endings.py](unit/public_release/test_shell_line_endings.py), [fixtures/enterprise_data_mcp_stub_server.py](fixtures/enterprise_data_mcp_stub_server.py).

P1 adds 52 offline public-demo checks and replaces an entrypoint AST assertion with deferred-lifecycle behavior coverage. Read measured counts and exact security assertions in P1_VALIDATION.json.

Validation and phase gates: [deployment plan](../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../docs/deployment/DIRECTORY_INDEX.md).
