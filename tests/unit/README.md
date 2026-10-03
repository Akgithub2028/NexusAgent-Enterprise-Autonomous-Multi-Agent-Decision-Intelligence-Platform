# Unit regression contracts

Reviewed on 2026-10-03 for P2, based on `5ce044b2dfec6b40dd2a7cc05401017975dc062d`; current source fingerprints are recorded below.
Review depth: supporting inventory / contracts.

Entry files: [public_release/test_shell_line_endings.py](public_release/test_shell_line_endings.py).

P2 regression includes actual server SIGTERM shutdown, mandatory audit failures, safe logging and concurrent bounded memory. Keep P1 visitor-isolation and default-deny checks.

Validation and phase gates: [deployment plan](../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../docs/deployment/DIRECTORY_INDEX.md).
