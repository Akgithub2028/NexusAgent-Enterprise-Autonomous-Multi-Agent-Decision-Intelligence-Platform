# Formal composition, execution and preflight

Reviewed on 2026-10-03 for P3/P4, based on `a7f4d5dcdde2bffaecd95340a63f41689e35c111`.
Review depth: runtime boundary traced.

Entry files: [configured_runtime.py](configured_runtime.py), [bootstrap.py](bootstrap.py), [executor.py](executor.py).

Configured runtime verifies a supplied immutable release before creating resources. Existing audit/memory/security and AsyncExitStack ownership remain; retrieval serving must use initialize_reader().

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
