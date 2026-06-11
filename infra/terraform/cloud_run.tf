# Placeholder image used on first terraform apply.
# After that, deploy.yml is the source of truth for Cloud Run config + images.
locals {
  placeholder = "gcr.io/cloudrun/placeholder"
}

resource "google_cloud_run_v2_service" "api" {
  name     = "radar-imovel-api"
  location = var.region

  template {
    service_account = google_service_account.api_sa.email
    containers {
      image = local.placeholder
    }
  }

  # deploy.yml manages image + env vars via gcloud run deploy.
  lifecycle { ignore_changes = [template] }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service" "frontend" {
  name     = "radar-imovel-frontend"
  location = var.region

  template {
    containers {
      image = local.placeholder
      ports { container_port = 8080 }
    }
  }

  lifecycle { ignore_changes = [template] }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_job" "collect_caixa" {
  name     = "radar-collect-caixa"
  location = var.region

  template {
    template {
      service_account = google_service_account.job_sa.email
      max_retries     = 1
      timeout         = "3600s"
      containers {
        image   = local.placeholder
        command = ["python", "jobs/collect_caixa.py"]
      }
    }
  }

  lifecycle { ignore_changes = [template] }

  depends_on = [google_project_service.apis]
}

# Fase 3: job genérico de coleta por banco. BANK é injetado por execução
# (gcloud run jobs execute radar-collect-bank --update-env-vars BANK=<bank>).
resource "google_cloud_run_v2_job" "collect_bank" {
  name     = "radar-collect-bank"
  location = var.region

  template {
    template {
      service_account = google_service_account.job_sa.email
      max_retries     = 1
      timeout         = "3600s"
      containers {
        image   = local.placeholder
        command = ["python", "-m", "jobs.collect_bank"]
        env {
          name  = "BANK"
          value = "" # default vazio; cada execução faz override
        }
      }
    }
  }

  lifecycle { ignore_changes = [template] }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_job" "process_alerts" {
  name     = "radar-process-alerts"
  location = var.region

  template {
    template {
      service_account = google_service_account.job_sa.email
      max_retries     = 2
      timeout         = "300s"
      containers {
        image   = local.placeholder
        command = ["python", "jobs/process_alerts.py"]
      }
    }
  }

  lifecycle { ignore_changes = [template] }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_job" "process_editais" {
  name     = "radar-process-editais"
  location = var.region

  template {
    template {
      service_account = google_service_account.job_sa.email
      max_retries     = 1
      timeout         = "600s"
      containers {
        image   = local.placeholder
        command = ["python", "jobs/process_editais.py"]
      }
    }
  }

  lifecycle { ignore_changes = [template] }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_job" "migrate" {
  name     = "radar-migrate"
  location = var.region

  template {
    template {
      service_account = google_service_account.job_sa.email
      max_retries     = 0
      timeout         = "300s"
      containers {
        image   = local.placeholder
        command = ["alembic", "upgrade", "head"]
      }
    }
  }

  lifecycle { ignore_changes = [template] }

  depends_on = [google_project_service.apis]
}

# ── Mapa de Risco ────────────────────────────────────────────────────────────
resource "google_cloud_run_v2_job" "calculate_risk" {
  count    = var.risk_job_enabled ? 1 : 0
  name     = "radar-calculate-risk"
  location = var.region

  template {
    template {
      service_account = google_service_account.job_sa.email
      max_retries     = 1
      timeout         = "600s"
      containers {
        image   = local.placeholder
        command = ["python", "-m", "jobs.calculate_risk"]
      }
    }
  }

  lifecycle { ignore_changes = [template] }

  depends_on = [google_project_service.apis]
}

# Allow unauthenticated access (Firebase JWT validated by FastAPI middleware)
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
