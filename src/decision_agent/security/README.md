# Identity, authorization, provider governance and audit

Reviewed on 2026-10-03 for P2, based on `5ce044b2dfec6b40dd2a7cc05401017975dc062d`; current source fingerprints are recorded below.
Review depth: runtime boundary traced.

Entry files: [models.py](models.py), [policy.py](policy.py), [governance.py](governance.py), [audit.py](audit.py).

P1 demo provenance and grants remain. P2 StdoutAuditSink flushes mandatory closed-schema events and poisons itself after write failure. Local JSONL chains/anchors remain unchanged. Cloud chains are per sink/process.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
