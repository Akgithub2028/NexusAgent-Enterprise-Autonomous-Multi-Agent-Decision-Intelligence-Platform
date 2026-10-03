# Scoped GitHub federation

Apply this **after** real P4 infrastructure, P5 ingestion job and P6 bootstrap of
`nexusagent-preview` and `nexusagent`. Existing resources are referenced; this module
does not create public services, ingest data, store secret values or mint a SA key.

Terraform 1.7+ / locked Google provider 6.50.0. Copy the nonsecret tfvars example into
an ignored file, verify numeric repository/owner IDs, then init/plan/review/apply.

```bash
terraform init
terraform plan -var-file=terraform.tfvars -out=release.tfplan
terraform apply release.tfplan
```

Federation accepts only repository ID `1354703369` / owner ID `181275449`, main, this exact
release workflow and the `nexus-release` GitHub environment subject. The release SA
can push to the one registry, update the existing preview/job, invoke both services,
act as the two runtime identities, read/create bucket metadata, and administer IAM
and revisions of the one production service. Project-level roles are read-only.
No Secret Manager accessor is granted to the release SA. Runtime identity attachment
still lets trusted deployment code change what those identities execute; review
main-branch changes and the protected environment accordingly.

Self TokenCreator supports short-lived impersonated HTTPS ID tokens, not external
service-account keys. No project-wide Cloud Run admin or project Editor is granted.
The production service-level admin role is necessary for explicit public/pause IAM
operations. Ingestion keeps its own writer secret access; preview/production get
only reader secret versions. See [P7 runbook](../../docs/deployment/P7_RELEASE.md).
