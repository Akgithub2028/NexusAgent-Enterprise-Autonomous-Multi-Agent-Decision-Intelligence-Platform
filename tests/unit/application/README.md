# Formal runtime lifecycle and executor regression

Reviewed on 2026-10-03 for P3/P4, based on `a7f4d5dcdde2bffaecd95340a63f41689e35c111`.

Entry files: [test_configured_runtime_bootstrap.py](test_configured_runtime_bootstrap.py), [test_formal_request_executor.py](test_formal_request_executor.py).

test_managed_release.py verifies socket validation, bounded engine configuration, reranker offline options and release checksum/config failure. Configured runtime doubles expose initialize_reader for serving.

Validation and source fingerprints: [deployment notes](../../../docs/deployment/README.md). Update this note with contract changes.
