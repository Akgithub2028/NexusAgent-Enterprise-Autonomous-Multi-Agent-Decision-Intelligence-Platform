# Offline federation plan

`offline.tftest.hcl` uses a mocked Google provider; it verifies numeric identity,
branch/workflow/environment restrictions and separate preview/production resources.
It creates no IAM resources and does not prove actual federation exchanges.

Run `terraform test` from the parent directory. Real OIDC and scoped-resource
permissions must pass before enabling GitHub releases.
