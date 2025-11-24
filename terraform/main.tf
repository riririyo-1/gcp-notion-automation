# -- Artifact Registry Repository --------------
resource "google_artifact_registry_repository" "notion_automation" {
  location      = var.region
  repository_id = "notion-automation"
  description   = "Docker repository for Notion automation"
  format        = "DOCKER"
}

# -- Secret Manager: API Keys --------------
resource "google_secret_manager_secret" "notion_api_key" {
  secret_id = "notion-api-key"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "notion_api_key" {
  secret      = google_secret_manager_secret.notion_api_key.id
  secret_data = var.notion_api_key
}

resource "google_secret_manager_secret" "notion_database_id" {
  secret_id = "notion-database-id"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "notion_database_id" {
  secret      = google_secret_manager_secret.notion_database_id.id
  secret_data = var.notion_database_id
}

resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "openai-api-key"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "openai_api_key" {
  secret      = google_secret_manager_secret.openai_api_key.id
  secret_data = var.openai_api_key
}

# -- Service Account for Cloud Run --------------
resource "google_service_account" "cloudrun_sa" {
  account_id   = "notion-automation-cloudrun"
  display_name = "Service Account for Notion Automation Cloud Run"
}

# Secret Manager へのアクセス権限
resource "google_secret_manager_secret_iam_member" "notion_api_key_access" {
  secret_id = google_secret_manager_secret.notion_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloudrun_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "notion_database_id_access" {
  secret_id = google_secret_manager_secret.notion_database_id.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloudrun_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "openai_api_key_access" {
  secret_id = google_secret_manager_secret.openai_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloudrun_sa.email}"
}

# -- Cloud Run Job --------------
resource "google_cloud_run_v2_job" "notion_automation" {
  name               = "notion-automation-job"
  location           = var.region
  deletion_protection = false

  template {
    template {
      service_account = google_service_account.cloudrun_sa.email

      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.notion_automation.repository_id}/notion-automation:latest"

        env {
          name = "NOTION_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.notion_api_key.secret_id
              version = "latest"
            }
          }
        }

        env {
          name = "NOTION_DATABASE_ID_ARTICLE"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.notion_database_id.secret_id
              version = "latest"
            }
          }
        }

        env {
          name = "OPENAI_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.openai_api_key.secret_id
              version = "latest"
            }
          }
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
      }

      max_retries = 3
      timeout     = "600s"
    }
  }
}

# -- Cloud Scheduler --------------
resource "google_cloud_scheduler_job" "notion_automation_trigger" {
  name             = "notion-automation-scheduler"
  description      = "Trigger Notion automation job periodically"
  schedule         = var.schedule
  time_zone        = "Asia/Tokyo"
  attempt_deadline = "320s"
  region           = var.region

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.notion_automation.name}:run"

    oauth_token {
      service_account_email = google_service_account.cloudrun_sa.email
    }
  }
}

# Cloud Run Job の実行権限をサービスアカウントに付与
resource "google_project_iam_member" "cloudrun_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.cloudrun_sa.email}"
}