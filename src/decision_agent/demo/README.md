# Local-only fixed-scope adapters

Reviewed on 2026-10-03 for P2, based on `5ce044b2dfec6b40dd2a7cc05401017975dc062d`; current source fingerprints are recorded below.
Review depth: runtime boundary traced.

Entry files: [local.py](local.py), [web.py](web.py).

The loopback demo remains local and now explicitly forces file audit with its external path, even if stdout mode was supplied. Cloud launch never uses these overrides.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
