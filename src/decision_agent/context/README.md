# Deterministic context and token budgets

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: supporting inventory / contracts.

Entry files: [manager.py](manager.py), [runtime.py](runtime.py), [conversation_memory.py](conversation_memory.py).

History and retrieved content remain untrusted bounded context. Deployment must not bypass existing prompt budgets or scope checks.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
