# Ephemeral and Redis session stores

Reviewed on 2026-10-03 for P2, based on `5ce044b2dfec6b40dd2a7cc05401017975dc062d`; current source fingerprints are recorded below.
Review depth: runtime boundary traced.

Entry files: [in_memory.py](in_memory.py), [redis_store.py](redis_store.py), [models.py](models.py).

P2 caps in-memory session count (default 1000), sweeps expired entries before new-session admission and rejects new history at capacity. Live history, TTL, deduplication and optimistic conflicts are preserved. Redis is deferred.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
