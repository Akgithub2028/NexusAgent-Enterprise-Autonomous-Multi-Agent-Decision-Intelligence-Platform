# Review the infrastructure graph with dummy billing, without contacting/provisioning GCP.
mock_provider "google" {
  mock_data "google_project" {
    defaults = { number = "123456789012" }
  }
}
run "least_privilege_infrastructure_plan" {
  command = plan
  variables {
    project_id            = "nexus-agent-510512"
    region                = "us-west1"
    billing_account_id    = "000000-000000-000000"
    monthly_budget_amount = 50
    budget_currency       = "USD"
  }
  assert {
    condition     = length(google_secret_manager_secret_iam_member.serving) == 4 && length(google_secret_manager_secret_iam_member.ingestion) == 1
    error_message = "Serving/ingestion secret access must remain separated."
  }
  assert {
    condition     = !contains(keys(google_secret_manager_secret_iam_member.serving), "nexus-vector-write-token")
    error_message = "Serving must never receive vector write credentials."
  }
  assert {
    condition     = google_sql_database_instance.demo.deletion_protection && google_sql_database_instance.demo.settings[0].disk_autoresize == false
    error_message = "Preserve SQL deletion protection and bounded disk."
  }
  assert {
    condition     = google_sql_database.synthetic.charset == "utf8mb4" && google_sql_database.synthetic.collation == "utf8mb4_0900_ai_ci"
    error_message = "Preserve synthetic fixture database encoding."
  }
  assert {
    condition     = google_billing_budget.demo.amount[0].specified_amount[0].units == "50"
    error_message = "The reviewed monthly alert budget must match operator inputs."
  }
}

run "private_ingestion_control" {
  command = plan
  variables {
    project_id            = "nexus-agent-510512"
    region                = "us-west1"
    billing_account_id    = "000000-000000-000000"
    monthly_budget_amount = 50
  }
  assert {
    condition     = google_storage_bucket.releases.public_access_prevention == "enforced" && google_storage_bucket.releases.uniform_bucket_level_access && google_storage_bucket.releases.versioning[0].enabled && !google_storage_bucket.releases.force_destroy
    error_message = "Release control metadata must remain private, versioned and protected from bulk deletion."
  }
  assert {
    condition     = google_storage_bucket_iam_member.ingestion_control.role == "roles/storage.objectUser"
    error_message = "Only bucket-scoped ingestion object access is required."
  }
}
