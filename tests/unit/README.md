# Unit regression contracts

Reviewed on 2026-10-03 for P1, based on `635a8ecc697754d798376626b0380f06d60e4cbf`; current source fingerprints are recorded below.
Review depth: supporting inventory / contracts.

Entry files: [public_release/test_shell_line_endings.py](public_release/test_shell_line_endings.py).

P1 validates visitor ownership with the actual formal executor, pre-execution table denial, quotas/cancellation/body bounds and the PyJWT claims-check regression. Runtime cloud/model validation remains a later gate.

Validation and phase gates: [deployment plan](../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../docs/deployment/DIRECTORY_INDEX.md).
