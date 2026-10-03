# Offline infrastructure review

`offline.tftest.hcl` uses Terraform's mock Google provider and explicit dummy billing
inputs to review the resource plan. It checks secret isolation, SQL protection/encoding
and the alert amount without contacting Google Cloud or creating resources.
Real managed deployment checks remain deferred until billing is linked.
