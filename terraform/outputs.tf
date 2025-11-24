output "artifact_registry_repository" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.notion_automation.repository_id}"
}

output "cloud_run_job_name" {
  description = "Cloud Run Job name"
  value       = google_cloud_run_v2_job.notion_automation.name
}

output "service_account_email" {
  description = "Service Account email"
  value       = google_service_account.cloudrun_sa.email
}