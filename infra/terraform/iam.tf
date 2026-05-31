resource "google_service_account" "api_sa" {
  account_id   = "radar-api"
  display_name = "Radar Imóvel — API"
}

resource "google_service_account" "job_sa" {
  account_id   = "radar-job"
  display_name = "Radar Imóvel — Cloud Run Jobs"
}

# API SA: Cloud SQL, Secret Manager
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

# Job SA: Cloud SQL, GCS, Pub/Sub, Secret Manager
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

# Cloud Run API: público (sem auth no nível do Cloud Run — auth feita pelo Firebase no FastAPI)
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
