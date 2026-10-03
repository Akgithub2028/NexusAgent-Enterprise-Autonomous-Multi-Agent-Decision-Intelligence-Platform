mock_provider "google" {}
run "restricted_federation" {
  command = plan
  variables {
    project_id          = "nexus-agent-510512"
    region              = "us-west1"
    repository_id       = "1354703369"
    repository_owner_id = "181275449"
    preview_service     = "nexusagent-preview"
    production_service  = "nexusagent"
    release_bucket      = "nexus-agent-510512-nexus-releases"
  }
  assert {
    condition     = strcontains(google_iam_workload_identity_pool_provider.github.attribute_condition, "assertion.repository_id == '1354703369'") && strcontains(google_iam_workload_identity_pool_provider.github.attribute_condition, "refs/heads/main") && strcontains(google_iam_workload_identity_pool_provider.github.attribute_condition, "environment:nexus-release")
    error_message = "Restrict federation to numeric repository identity, release branch/workflow and protected environment."
  }
  assert {
    condition     = google_cloud_run_service_iam_member.production_operator.service != google_cloud_run_service_iam_member.preview_deployer.service && length(google_service_account_iam_member.runtime_user) == 2
    error_message = "Preview must remain separate; only two runtime identities can be attached."
  }
}
