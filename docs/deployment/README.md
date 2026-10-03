# Deployment implementation and acceptance ledger

Reviewed 2026-10-04. One FastAPI container serves the Workbench and scoped decision
runtime; managed SQL/vectors and independent ingestion remain the target.

| Phase | Implementation | Acceptance |
| --- | --- | --- |
| P0 audit/baseline | Complete | Local recorded baseline |
| P1 public-demo boundary | Complete | Fixed scopes, visitor ownership and admission tested |
| P2 cloud runtime | Complete | Lifecycle, bounded memory and mandatory stdout audit tested |
| P3 reproducible CPU image | Complete | Real offline model/wheel/MCP container checks passed |
| P4 managed adapters/infrastructure | Complete | Zilliz/local SQL checks passed; actual Google provisioning and scoped provider credentials pending |
| P5 independent ingestion | Complete | Offline regression passed; real first/repeat jobs pending |
| P6 restricted serving | Complete | Local/deployment tooling checks passed; managed deployment and measurements pending |
| P7 gated CI/CD | Complete | Workflow/OIDC plan/release guards prepared; federation and live release pending |

**Blocking state:** authenticated billing recheck returnedfalse. Owner authorized
explicit dummy/offline preparation while billing setup is unresolved. No live URL,
paid cloud provisioning or live LLM completion is claimed. GitHub's release environment
is protected and its enable variable isfalse. LIVE_ACCEPTANCE remainsblocked.

Start with [current handoff](../CODEX_HANDOFF.md), then:

- [P7 release/OIDC/public/rollback runbook](P7_RELEASE.md)
- [P6 restricted deployment and measurements](P6_RESTRICTED_DEPLOYMENT.md)
- [P5 versioned ingestion/promotion](P5_INGESTION.md)
- [P3/P4 implementation and managed gates](P3_P4_IMPLEMENTATION.md)
- [Cloud infrastructure/operator guide](../../deploy/cloud-run/README.md)
- [OIDC resource scope](../../deploy/github-oidc/README.md)
- [Implementation plan](IMPLEMENTATION_PLAN.md)
- [P1 boundary](P1_PUBLIC_DEMO.md), [P2 runtime](P2_CLOUD_RUNTIME.md), [P0 audit](P0_AUDIT.md)
- [P0 baseline](P0_BASELINE.json), [P1 evidence](P1_VALIDATION.json), [P2 evidence](P2_VALIDATION.json)
- [P3/P4 evidence](P3_P4_VALIDATION.json), [P5 evidence](P5_VALIDATION.json), [P6 evidence](P6_VALIDATION.json), [P7 evidence](P7_VALIDATION.json)
- [Directory index](DIRECTORY_INDEX.md) and [fingerprints](DIRECTORY_MANIFEST.json)

Keep historical evidence unchanged. Record real measurements before advancing live
acceptance; do not relabel mock plans/local sockets as managed success. The P0
historical dependency findings were remediated in P1; current CI audits remain the
appropriate source for present dependency results.
