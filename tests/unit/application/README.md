# Formal runtime lifecycle and executor regression

Reviewed on 2026-10-03 for P1, based on `635a8ecc697754d798376626b0380f06d60e4cbf`.

Entry files: [test_configured_runtime_bootstrap.py](test_configured_runtime_bootstrap.py), [test_formal_request_executor.py](test_formal_request_executor.py).

P1 replaces the old main AST shape assertion with deferred startup/failure/cleanup behavior. Preserve formal ownership and governance invariants.

Validation and source fingerprints: [deployment notes](../../../docs/deployment/README.md). Update this note with contract changes.
