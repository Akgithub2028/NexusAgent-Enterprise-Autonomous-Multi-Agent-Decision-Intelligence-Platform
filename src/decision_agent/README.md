# NexusAgent application package

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: supporting inventory / contracts.

Entry files: [main.py](main.py), [application/configured_runtime.py](application/configured_runtime.py).

Main already owns deferred formal bootstrap. Reuse its architecture; public identity, cloud audit and managed connection options are missing boundaries.

Validation and phase gates: [deployment plan](../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../docs/deployment/DIRECTORY_INDEX.md).
