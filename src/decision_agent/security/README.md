# Identity, authorization, provider governance and audit

Reviewed on 2026-10-03 for P1, based on `635a8ecc697754d798376626b0380f06d60e4cbf`; current source fingerprints are recorded below.
Review depth: runtime boundary traced.

Entry files: [models.py](models.py), [policy.py](policy.py), [governance.py](governance.py), [audit.py](audit.py).

P1 adds explicit demo/demo_cookie provenance and a factory requiring the verified visitor subject; no human/test identity is fabricated. Existing default-deny and file audit remain. P2 adds cloud audit semantics.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
