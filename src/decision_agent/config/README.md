# Environment-backed settings

Reviewed on 2026-10-03 for P1, based on `635a8ecc697754d798376626b0380f06d60e4cbf`; current source fingerprints are recorded below.
Review depth: runtime boundary traced.

Entry files: [settings.py](settings.py).

P1 adds deployment mode, non-placeholder public settings, signing secret and bounded admission controls. P2 adds memory/audit settings, P3 offline reranker controls and P4 socket/AUTOINDEX options.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
