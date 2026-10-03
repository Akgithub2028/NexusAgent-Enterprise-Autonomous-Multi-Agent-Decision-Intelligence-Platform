# Public release regression contracts

P7 tests cover the exact six-job CI gate, incomplete managed acceptance, immutable
candidate matching, saved-revision rollback, safe snapshots and verified badge URLs.
All checks use local substitutes and make no cloud mutations.

Run from the repository root:

```bash
.venv/bin/pytest -q tests/unit/public_release
```

These tests do not establish managed deployment acceptance. Preserve the blocked
live record until actual provider operations and measurements are documented in the
[P7 runbook](../../../docs/deployment/P7_RELEASE.md).
