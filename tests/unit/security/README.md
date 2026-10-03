# Authorization, governance and audit regression

Reviewed on 2026-10-03 for P2, based on `5ce044b2dfec6b40dd2a7cc05401017975dc062d`.

Entry file: [test_stdout_audit.py](test_stdout_audit.py).

P2 tests mandatory stdout chains, short writes/flush failure, poisoned sinks, provider admission/completion failure and actual executor response-release denial. Preserve file-integrity and fixed-grant tests.

Contract and validation: [P2 runtime](../../../docs/deployment/P2_CLOUD_RUNTIME.md). Update this note with source changes.
