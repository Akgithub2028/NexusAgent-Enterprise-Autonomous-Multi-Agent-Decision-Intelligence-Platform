# FastAPI transport, readiness and identity seam

Reviewed on 2026-10-03 for P1, based on `635a8ecc697754d798376626b0380f06d60e4cbf`; current source fingerprints are recorded below.
Review depth: runtime boundary traced.

Entry files: [public_demo.py](public_demo.py), [app.py](app.py), [runtime.py](runtime.py), [routes.py](routes.py), [security.py](security.py).

P1 public_demo.py owns HMAC visitor bootstrap, fixed grants, exact-origin/Fetch Metadata checks and bounded admission/body reads. The formal lifecycle and default rejection remain; P2 cloud audit is pending.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
