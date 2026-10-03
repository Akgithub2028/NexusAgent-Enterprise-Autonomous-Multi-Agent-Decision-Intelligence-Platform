# Ephemeral and Redis session stores

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: runtime boundary traced.

Entry files: [in_memory.py](in_memory.py), [redis_store.py](redis_store.py), [models.py](models.py).

P2 adds total-session bounds and expiry cleanup, preserving versions/TTL/deduplication. Redis auth URLs are currently restricted; Redis is deferred.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
