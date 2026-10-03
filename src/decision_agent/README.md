# NexusAgent application package

Reviewed on 2026-10-03 for P3/P4, based on `a7f4d5dcdde2bffaecd95340a63f41689e35c111`.
Review depth: supporting inventory / contracts.

Entry files: [cloud.py](cloud.py), [main.py](main.py), [application/configured_runtime.py](application/configured_runtime.py).

P3 release.py checks immutable assets before resources open. cloud.py remains the single-worker P2 launcher. P4 adds managed sockets/AUTOINDEX and a reader-only store lifecycle.

Validation and phase gates: [deployment plan](../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../docs/deployment/DIRECTORY_INDEX.md).
