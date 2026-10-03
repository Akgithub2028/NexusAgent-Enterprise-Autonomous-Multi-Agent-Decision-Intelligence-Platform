# Explicit demos, ingestion and evaluation commands

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: supporting inventory / contracts.

Entry files: [run_local_web_demo.py](run_local_web_demo.py), [initialize_knowledge_corpus.py](initialize_knowledge_corpus.py), [validate_dependency_lock.py](validate_dependency_lock.py).

Serving must not invoke ingestion at startup. P5 reuses the explicit ingestion script; local demo security/settings remain local-only.

Validation and phase gates: [deployment plan](../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../docs/deployment/DIRECTORY_INDEX.md).
