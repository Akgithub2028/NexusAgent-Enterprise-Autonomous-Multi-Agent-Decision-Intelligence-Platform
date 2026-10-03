# Local parsers and deterministic chunking

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: supporting inventory / contracts.

Entry files: [parsers.py](parsers.py), [chunking.py](chunking.py), [clause_aware_chunking.py](clause_aware_chunking.py).

P5 uses an independent job with immutable corpus identity. Serving reads generated chunks and does not parse/upsert documents at startup.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).

P5 adds independent versioned ingestion, distributed generation locks and completion/
promotion gates. See [P5 runbook](../../../docs/deployment/P5_INGESTION.md). Managed execution awaits billing/P4 prerequisites.
