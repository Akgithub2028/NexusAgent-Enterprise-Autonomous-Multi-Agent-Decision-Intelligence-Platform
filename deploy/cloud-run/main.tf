terraform {
  required_version = ">= 1.7, < 2.0"
  required_providers {
    google = { source = "hashicorp/google", version = "6.50.0" }
  }
}
provider "google" {
  project = var.project_id
  region  = var.region
}
variable "project_id" { type = string }
variable "region" { type = string }
variable "billing_account_id" { type = string }
variable "monthly_budget_amount" {
  type = number
  validation {
    condition     = var.monthly_budget_amount > 0
    error_message = "Set an explicit positive monthly budget; alerts do not stop spending."
  }
}
variable "budget_currency" {
  type    = string
  default = "USD"
}
variable "sql_tier" {
  type    = string
  default = "db-f1-micro"
}
locals {
  apis              = toset(["artifactregistry.googleapis.com", "sqladmin.googleapis.com", "secretmanager.googleapis.com", "run.googleapis.com", "billingbudgets.googleapis.com", "iam.googleapis.com", "storage.googleapis.com"])
  serving_secrets   = toset(["nexus-groq-key", "nexus-demo-signing-key", "nexus-db-reader-password", "nexus-vector-read-token"])
  ingestion_secrets = toset(["nexus-vector-write-token"])
}
resource "google_project_service" "api" {
  for_each           = local.apis
  service            = each.value
  disable_on_destroy = false
}
resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = "nexusagent"
  format        = "DOCKER"
  depends_on    = [google_project_service.api]
}
resource "google_service_account" "serving" {
  account_id   = "nexus-serving"
  display_name = "NexusAgent serving reader"
}
resource "google_service_account" "ingestion" {
  account_id   = "nexus-ingestion"
  display_name = "NexusAgent vector ingestion writer"
}
resource "google_project_iam_member" "sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.serving.email}"
}
resource "google_secret_manager_secret" "runtime" {
  for_each  = setunion(local.serving_secrets, local.ingestion_secrets)
  secret_id = each.value
  replication {
    auto {}
  }
  depends_on = [google_project_service.api]
}
resource "google_secret_manager_secret_iam_member" "serving" {
  for_each  = local.serving_secrets
  secret_id = google_secret_manager_secret.runtime[each.value].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.serving.email}"
}
resource "google_secret_manager_secret_iam_member" "ingestion" {
  for_each  = local.ingestion_secrets
  secret_id = google_secret_manager_secret.runtime[each.value].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ingestion.email}"
}
resource "google_sql_database_instance" "demo" {
  name                = "nexus-demo-mysql"
  region              = var.region
  database_version    = "MYSQL_8_0"
  deletion_protection = true
  settings {
    tier              = var.sql_tier
    availability_type = "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = 10
    disk_autoresize   = false
    backup_configuration { enabled = true }
    ip_configuration { ipv4_enabled = true }
    database_flags {
      name  = "default_time_zone"
      value = "+08:00"
    }
  }
  depends_on = [google_project_service.api]
}
resource "google_sql_database" "synthetic" {
  name      = "enterprise_operations"
  instance  = google_sql_database_instance.demo.name
  charset   = "utf8mb4"
  collation = "utf8mb4_0900_ai_ci"
}
resource "google_billing_budget" "demo" {
  billing_account = var.billing_account_id
  display_name    = "NexusAgent demo monthly alert"
  budget_filter {
    projects = ["projects/${data.google_project.current.number}"]
  }
  amount {
    specified_amount {
      currency_code = var.budget_currency
      units         = tostring(floor(var.monthly_budget_amount))
      nanos         = floor((var.monthly_budget_amount - floor(var.monthly_budget_amount)) * 1000000000)
    }
  }
  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 0.9 }
  threshold_rules { threshold_percent = 1.0 }
}
data "google_project" "current" {}
output "sql_connection_name" { value = google_sql_database_instance.demo.connection_name }
output "serving_identity" { value = google_service_account.serving.email }
output "ingestion_identity" { value = google_service_account.ingestion.email }
output "registry" { value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}" }

# P5 control metadata only; knowledge payloads stay in the image and vector store.
resource "google_storage_bucket" "releases" {
  name                        = "${var.project_id}-nexus-releases"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  versioning { enabled = true }
  depends_on = [google_project_service.api]
}
resource "google_storage_bucket_iam_member" "ingestion_control" {
  bucket = google_storage_bucket.releases.name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.ingestion.email}"
}
output "release_control_bucket" { value = google_storage_bucket.releases.name }
