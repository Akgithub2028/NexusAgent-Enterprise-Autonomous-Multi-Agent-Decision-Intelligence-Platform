# Explicit demos, ingestion and evaluation commands

Reviewed on 2026-10-03 for P3/P4, based on `a7f4d5dcdde2bffaecd95340a63f41689e35c111`.
Review depth: supporting inventory / contracts.

Entry files: [run_local_web_demo.py](run_local_web_demo.py), [initialize_knowledge_corpus.py](initialize_knowledge_corpus.py), [validate_dependency_lock.py](validate_dependency_lock.py).

P3 prepare_cloud_release.py produces immutable corpus/model manifests; validate_cloud_image.py exercises offline installed models/UI/MCP. P4 manage_cloud_sql_demo.py performs admin seed and independent reader checks; verify_managed_vector.py owns and cleans only an isolated test collection. Never run admin seed during serving.

Validation and phase gates: [deployment plan](../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../docs/deployment/DIRECTORY_INDEX.md).

P5 adds independent versioned ingestion, distributed generation locks and completion/
promotion gates. See [P5 runbook](../docs/deployment/P5_INGESTION.md). Managed execution awaits billing/P4 prerequisites.
