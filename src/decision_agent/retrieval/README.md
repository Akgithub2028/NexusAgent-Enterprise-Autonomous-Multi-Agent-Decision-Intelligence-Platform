# Dense/BM25 fusion, reranking and parent evidence

Reviewed on 2026-10-03 for P3/P4, based on `a7f4d5dcdde2bffaecd95340a63f41689e35c111`.
Review depth: runtime boundary traced.

Entry files: [factory.py](factory.py), [pipeline.py](pipeline.py), [milvus_store.py](milvus_store.py), [embeddings.py](embeddings.py), [reranking.py](reranking.py).

P3 reranker gains cache/local-only loading with remote code disabled. P4 AUTOINDEX uses empty parameters; HNSW validation remains. Serving validates existing collections through initialize_reader without provisioning/load/upsert/delete; ingestion retains writer initialization. Local/remote IDs must agree.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).

P6 native inference calls retain thread serialization when an awaiting request is cancelled.
