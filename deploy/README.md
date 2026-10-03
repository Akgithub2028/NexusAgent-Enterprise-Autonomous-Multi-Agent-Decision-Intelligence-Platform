# Deployment assets

[cloud-run](cloud-run/README.md) contains the verified CPU image dependency locks,
Terraform infrastructure and operator configuration. No public service or ingestion job
is deployed yet. Owner-authorized dummy configuration supports offline review; billing must be linked
before actual Google infrastructure provisioning.
Keep all credentials, local Terraform state/plans/inputs and CLI caches out of Git.
