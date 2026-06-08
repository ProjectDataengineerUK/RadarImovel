# ── Application service accounts ────────────────────────────────────────────

resource "google_service_account" "api_sa" {
  account_id   = "radar-api"
  display_name = "Radar Imóvel — API"
}

resource "google_service_account" "job_sa" {
  account_id   = "radar-job"
  display_name = "Radar Imóvel — Cloud Run Jobs"
}

# API SA permissions
resource "google_project_iam_member" "api_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

resource "google_project_iam_member" "api_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

resource "google_project_iam_member" "api_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

# Job SA permissions
resource "google_project_iam_member" "job_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.job_sa.email}"
}

resource "google_project_iam_member" "job_gcs" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.job_sa.email}"
}

resource "google_project_iam_member" "job_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.editor"
  member  = "serviceAccount:${google_service_account.job_sa.email}"
}

resource "google_project_iam_member" "job_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.job_sa.email}"
}

# ── GitHub Actions — Workload Identity Federation ────────────────────────────

resource "google_service_account" "github_actions" {
  account_id   = "github-actions"
  display_name = "GitHub Actions — CI/CD"
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Provider"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  # Only allow tokens from this specific repo
  attribute_condition = "assertion.repository == '${var.github_repo}'"
}

resource "google_service_account_iam_member" "github_wif" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}

# github-actions SA permissions
resource "google_project_iam_member" "gh_artifact_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "gh_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# Needed to deploy Cloud Run services/jobs that run as specific SAs
resource "google_service_account_iam_member" "gh_actas_api_sa" {
  service_account_id = google_service_account.api_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_service_account_iam_member" "gh_actas_job_sa" {
  service_account_id = google_service_account.job_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_actions.email}"
}
