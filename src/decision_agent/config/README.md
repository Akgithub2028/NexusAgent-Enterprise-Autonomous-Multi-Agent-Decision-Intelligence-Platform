# Environment-backed settings

Reviewed on 2026-10-03 for P3/P4, based on `a7f4d5dcdde2bffaecd95340a63f41689e35c111`.
Review depth: runtime boundary traced.

Entry files: [settings.py](settings.py).

P3 adds optional release manifest and reranker cache/offline configuration. P4 validates Cloud SQL sockets, bounded pools and AUTOINDEX. Public HTTPS/cookie/fixed-grant requirements remain.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
