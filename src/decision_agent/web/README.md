# Package-local Web Workbench assets

Reviewed on 2026-10-03 for P2, based on `5ce044b2dfec6b40dd2a7cc05401017975dc062d`; current source fingerprints are recorded below.
Review depth: runtime boundary traced.

Entry files: [index.html](index.html), [app.js](app.js), [styles.css](styles.css).

P1 visitor bootstrap and HTTP errors remain. P2 makes ephemeral history loss on expiry, restart and rollout visible. Browser session labels do not provide persistent server history.

Validation and phase gates: [deployment plan](../../../docs/deployment/IMPLEMENTATION_PLAN.md).
Update this note with source changes; check its source fingerprint in the [directory index](../../../docs/deployment/DIRECTORY_INDEX.md).
