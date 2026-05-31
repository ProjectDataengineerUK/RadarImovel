resource "google_cloud_run_v2_service" "api" {
  name     = "radar-imovel-api"
  location = var.region

  template {
    service_account = google_service_account.api_sa.email

    containers {
      image = var.api_image

      env {
        name  = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "TELEGRAM_BOT_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.telegram_token.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "FIREBASE_CREDENTIALS_JSON"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.firebase_creds.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "PUBSUB_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCS_BUCKET_RAW"
        value = google_storage_bucket.radar_raw.name
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_job" "collect_caixa" {
  name     = "collect-caixa"
  location = var.region

  template {
    template {
      service_account = google_service_account.job_sa.email
      max_retries     = 1
      timeout         = "3600s"  # 1 hora por UF

      containers {
        image   = var.job_image
        command = ["python", "jobs/collect_caixa.py"]

        env {
          name  = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.db_url.secret_id
              version = "latest"
            }
          }
        }
        env {
          name  = "TELEGRAM_BOT_TOKEN"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.telegram_token.secret_id
              version = "latest"
            }
          }
        }
        env {
          name  = "FIREBASE_CREDENTIALS_JSON"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.firebase_creds.secret_id
              version = "latest"
            }
          }
        }
        env {
          name  = "PUBSUB_PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "GCS_BUCKET_RAW"
          value = google_storage_bucket.radar_raw.name
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_job" "process_alerts" {
  name     = "process-alerts"
  location = var.region

  template {
    template {
      service_account = google_service_account.job_sa.email
      max_retries     = 2
      timeout         = "300s"

      containers {
        image   = var.job_image
        command = ["python", "jobs/process_alerts.py"]

        env {
          name  = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.db_url.secret_id
              version = "latest"
            }
          }
        }
        env {
          name  = "TELEGRAM_BOT_TOKEN"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.telegram_token.secret_id
              version = "latest"
            }
          }
        }
        env {
          name  = "FIREBASE_CREDENTIALS_JSON"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.firebase_creds.secret_id
              version = "latest"
            }
          }
        }
        env {
          name  = "PUBSUB_PROJECT_ID"
          value = var.project_id
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
      }
    }
  }

  depends_on = [google_project_service.apis]
}
