# GitHub automation

Reviewed on 2026-10-03 at source `2e2b34c220158c1711409ddb1335fba00fbe375f`.
Review depth: supporting inventory / contracts.

Entry files: [CI](workflows/ci.yml), [cloud release](workflows/release.yml).

Six CI checks validate the source. P7 adds image builds and release automation; cloud federation and live deployment await managed acceptance.

Validation and phase gates: [deployment plan](../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../docs/deployment/DIRECTORY_INDEX.md).

P7 adds a disabled-by-default OIDC release workflow. Preserve six CI gates; protected environment/release enablement and real acceptance control live operations.

This directory note is named `AUTOMATION.md` because GitHub gives a `.github/README`
priority over the root project README. Keep the project landing page in
[the root README](../README.md); do not reintroduce a README directly under `.github`.
See [GitHub README selection](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes).
