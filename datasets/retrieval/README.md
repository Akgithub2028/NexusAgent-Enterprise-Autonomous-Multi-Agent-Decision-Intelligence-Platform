# Retrieval evaluation fixtures

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: supporting inventory / contracts.

Entry files: [.gitkeep](.gitkeep), [m2b2c_dense_corpus.jsonl](m2b2c_dense_corpus.jsonl), [m2b2c_dense_queries.jsonl](m2b2c_dense_queries.jsonl).

Evaluation inputs are separate from the serving corpus. Use frozen evidence checks for regression; exclude unnecessary reports from the runtime image.

Validation and phase gates: [deployment plan](../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../docs/deployment/DIRECTORY_INDEX.md).
