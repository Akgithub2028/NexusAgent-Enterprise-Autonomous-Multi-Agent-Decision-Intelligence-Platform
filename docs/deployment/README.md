# Cloud deployment preparation

P0 source snapshot: `2e2b34c220158c1711409ddb1335fba00fbe375f`.
P1 reviewed on 2026-10-03, based on `635a8ecc697754d798376626b0380f06d60e4cbf`.

P0 established the audit, plan, directory notes and baseline. P1 implements opt-in
public-demo identity, fixed grants and bounded admission, and remediates the reported
dependency findings. P2 adds the container launcher, bounded ephemeral memory and mandatory stdout audit
with structured logging. No cloud service has been deployed. P3 has not started.

- [Implementation plan and phase gates](IMPLEMENTATION_PLAN.md)
- [P2 runtime, memory and audit contract](P2_CLOUD_RUNTIME.md)
- [P2 validation evidence](P2_VALIDATION.json)
- [P1 public-demo implementation and API contract](P1_PUBLIC_DEMO.md)
- [P1 validation evidence](P1_VALIDATION.json)
- [P0 source audit and completion checklist](P0_AUDIT.md)
- [Measured check results](P0_BASELINE.json)
- [Dependency advisory inventory](P0_DEPENDENCY_AUDIT.json)
- [Directory navigation and maintenance](DIRECTORY_INDEX.md)
- [Directory source fingerprints](DIRECTORY_MANIFEST.json)
- [P0 documentation validation](P0_VALIDATION.json)

Read the audit before implementing a phase. Update affected directory READMEs and this
status in the same commit as their implementation. A source fingerprint identifies
when a note needs review; it does not automatically rewrite the note.

P0's historical scan reported 24 advisories in three packages. P1 updates those pins;
the new resolving and pinned-package audits report zero known vulnerabilities.
