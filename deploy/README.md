# Deployment boundaries

[cloud-run](cloud-run/README.md) owns managed-state infrastructure, immutable corpus/
image configuration and phase runbooks. [github-oidc](github-oidc/README.md) adds
optional federation against existing preview/production/job resources.

These roots never store secret values or build a fictional live URL. Keep Terraform
state and operator input files ignored; actual provisioning awaits linked billing.
