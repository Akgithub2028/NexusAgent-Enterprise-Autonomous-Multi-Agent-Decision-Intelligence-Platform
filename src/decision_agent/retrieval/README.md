# Dense/BM25 fusion, reranking and parent evidence

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: runtime boundary traced.

Entry files: [factory.py](factory.py), [pipeline.py](pipeline.py), [milvus_store.py](milvus_store.py), [embeddings.py](embeddings.py), [reranking.py](reranking.py).

Serving requires exact local/vector ID agreement. P3 adds offline reranker controls; P4 separates provisioning and supports AUTOINDEX without weakening schema/filter validation.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
