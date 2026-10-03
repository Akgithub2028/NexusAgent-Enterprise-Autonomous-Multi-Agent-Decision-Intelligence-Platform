# NexusAgent application package

Reviewed on 2026-10-03 for P2, based on `5ce044b2dfec6b40dd2a7cc05401017975dc062d`; current source fingerprints are recorded below.
Review depth: supporting inventory / contracts.

Entry files: [cloud.py](cloud.py), [main.py](main.py), [application/configured_runtime.py](application/configured_runtime.py).

P2 cloud.py launches one worker on validated PORT; main.py preserves the ASGI factory. Bounded memory and stdout audit reuse formal composition. P3 image/model packaging remains.

Validation and phase gates: [deployment plan](../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../docs/deployment/DIRECTORY_INDEX.md).
