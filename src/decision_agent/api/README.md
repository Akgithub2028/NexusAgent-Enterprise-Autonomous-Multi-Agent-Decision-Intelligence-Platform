# FastAPI transport, readiness and identity seam

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: runtime boundary traced.

Entry files: [app.py](app.py), [runtime.py](runtime.py), [routes.py](routes.py), [security.py](security.py).

P1 adds opt-in public identity/admission. Preserve rejecting default, package UI routes and unavailable readiness on failed bootstrap.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
