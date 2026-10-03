# Package-local Web Workbench assets

Reviewed on 2026-10-03 for P1, based on `635a8ecc697754d798376626b0380f06d60e4cbf`; current source fingerprints are recorded below.
Review depth: runtime boundary traced.

Entry files: [index.html](index.html), [app.js](app.js), [styles.css](styles.css).

P1 bootstraps the signed visitor before each execution and reports 401/429. Local/private bootstrap 404 preserves their contract. New Session rotates only its label; browser cookies remain HttpOnly and history remains ephemeral.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
