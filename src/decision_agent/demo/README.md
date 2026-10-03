# Local-only fixed-scope adapters

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: runtime boundary traced.

Entry files: [local.py](local.py), [web.py](web.py).

Loopback-only resolver and local audit overrides stay local. P1 uses separate public visitor identity and fixed audited grants.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
