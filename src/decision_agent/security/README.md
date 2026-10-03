# Identity, authorization, provider governance and audit

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: runtime boundary traced.

Entry files: [models.py](models.py), [policy.py](policy.py), [governance.py](governance.py), [audit.py](audit.py).

P1 adds truthful visitor provenance; P2 cloud audit keeps payload-free fail-closed semantics. Do not equate cloud logging with global hash-chain delivery guarantees.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
