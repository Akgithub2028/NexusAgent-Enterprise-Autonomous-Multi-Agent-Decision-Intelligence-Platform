# Session retention and optimistic-concurrency regression

Reviewed on 2026-10-03 for P2, based on `5ce044b2dfec6b40dd2a7cc05401017975dc062d`.

Entry file: [test_in_memory.py](test_in_memory.py).

P2 covers capacity denial without live eviction, expiry reclamation, idempotence and concurrent admissions. Existing compaction/TTL/version behavior remains.

Contract and validation: [P2 runtime](../../../docs/deployment/P2_CLOUD_RUNTIME.md). Update this note with source changes.
