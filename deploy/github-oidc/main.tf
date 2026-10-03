terraform {
  required_version = ">= 1.7, < 2.0"
  required_providers {
    google = { source = "hashicorp/google", version = "6.50.0" }
  }
}
provider "google" { project = var.project_id }
variable "project_id" { type = string }
variable "region" { type = string }
variable "repository_id" { type = string }
variable "repository_owner_id" { type = string }
variable "preview_service" { type = string }
variable "production_service" { type = string }
variable "release_bucket" { type = string }
variable "repository" {
  type    = string
  default = "Akgithub2028/NexusAgent-Enterprise-Autonomous-Multi-Agent-Decision-Intelligence-Platform"
}
data "google_project" "current" {}
resource "google_project_service" "federation" {
  for_each           = toset(["iam.googleapis.com", "iamcredentials.googleapis.com", "sts.googleapis.com"])
  service            = each.value
  disable_on_destroy = false
}
resource "google_service_account" "release" {
  account_id   = "nexus-release"
  display_name = "NexusAgent scoped GitHub release operator"
}
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "nexus-github"
  depends_on                = [google_project_service.federation]
}
resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "release"
  attribute_mapping = {
    "google.subject"                = "assertion.sub"
    "attribute.repository_id"       = "assertion.repository_id"
    "attribute.repository_owner_id" = "assertion.repository_owner_id"
    "attribute.ref"                 = "assertion.ref"
    "attribute.workflow_ref"        = "assertion.workflow_ref"
  }
  attribute_condition = "assertion.repository_id == '${var.repository_id}' && assertion.repository_owner_id == '${var.repository_owner_id}' && assertion.ref == 'refs/heads/main' && assertion.workflow_ref == '${var.repository}/.github/workflows/release.yml@refs/heads/main' && assertion.sub == 'repo:${var.repository}:environment:nexus-release'"
  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
}
resource "google_service_account_iam_member" "federated" {
  service_account_id = google_service_account.release.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository_id/${var.repository_id}"
}
# Short-lived ID tokens for HTTPS invocation using this identity itself.
resource "google_service_account_iam_member" "self_token" {
  service_account_id = google_service_account.release.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.release.email}"
}
resource "google_artifact_registry_repository_iam_member" "push" {
  location   = var.region
  repository = "nexusagent"
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.release.email}"
}
resource "google_project_iam_member" "runtime_reader" {
  project = var.project_id
  role    = "roles/run.viewer"
  member  = "serviceAccount:${google_service_account.release.email}"
}
resource "google_project_iam_member" "project_reader" {
  project = var.project_id
  role    = "roles/browser"
  member  = "serviceAccount:${google_service_account.release.email}"
}
resource "google_cloud_run_service_iam_member" "preview_deployer" {
  location = var.region
  service  = var.preview_service
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.release.email}"
}
resource "google_cloud_run_service_iam_member" "preview_invoker" {
  location = var.region
  service  = var.preview_service
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.release.email}"
}
resource "google_cloud_run_service_iam_member" "production_operator" {
  location = var.region
  service  = var.production_service
  role     = "roles/run.admin"
  member   = "serviceAccount:${google_service_account.release.email}"
}
resource "google_cloud_run_service_iam_member" "production_invoker" {
  location = var.region
  service  = var.production_service
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.release.email}"
}
resource "google_cloud_run_v2_job_iam_member" "ingestion" {
  location = var.region
  name     = "nexus-ingestion"
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.release.email}"
}
resource "google_service_account_iam_member" "runtime_user" {
  for_each           = toset(["nexus-serving", "nexus-ingestion"])
  service_account_id = "projects/${var.project_id}/serviceAccounts/${each.value}@${var.project_id}.iam.gserviceaccount.com"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.release.email}"
}
resource "google_storage_bucket_iam_member" "evidence" {
  for_each = toset(["roles/storage.objectViewer", "roles/storage.objectCreator"])
  bucket   = var.release_bucket
  role     = each.value
  member   = "serviceAccount:${google_service_account.release.email}"
}
output "workload_identity_provider" { value = google_iam_workload_identity_pool_provider.github.name }
output "release_service_account" { value = google_service_account.release.email }
