# API transport and public-demo regression

Reviewed on 2026-10-03 for P1, based on `635a8ecc697754d798376626b0380f06d60e4cbf`.

Entry files: [test_agent_api.py](test_agent_api.py), [test_public_demo.py](test_public_demo.py).

P1 tests require no real provider/database credentials. Keep cross-visitor memory, scope, CSRF, limits and cancellation coverage.

Validation and source fingerprints: [deployment notes](../../../docs/deployment/README.md). Update this note with contract changes.

P6 covers deadline/admission cancellation, private deployment gates, secure measurement projections and native-thread serialization.
