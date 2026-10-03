# Installable Python source tree

Reviewed on 2026-10-03 for P3/P4, based on `a7f4d5dcdde2bffaecd95340a63f41689e35c111`.
Review depth: supporting inventory / contracts.

Entry files: [decision_agent/main.py](decision_agent/main.py).

P3 packages the installed CPU runtime/UI and immutable model/corpus assets; P4 separates serving readers from provisioning. See deployment report for managed gates.

Validation and phase gates: [deployment plan](../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../docs/deployment/DIRECTORY_INDEX.md).
