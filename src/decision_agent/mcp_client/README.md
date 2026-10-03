# Owned stdio subprocess transport

Reviewed on 2026-10-03 for P3/P4, based on `a7f4d5dcdde2bffaecd95340a63f41689e35c111`.
Review depth: runtime boundary traced.

Entry files: [enterprise_data_client.py](enterprise_data_client.py), [contracts.py](contracts.py).

P4 explicitly whitelists socket/pool settings into the child. Provider/vector/cookie secrets remain excluded; installed stdio command and payload/schema contracts stay intact.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
