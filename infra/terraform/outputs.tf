output "api_url" {
  description = "Cloud Run API URL"
  value       = google_cloud_run_v2_service.api.uri
}

output "frontend_url" {
  description = "Cloud Run Frontend URL"
  value       = google_cloud_run_v2_service.frontend.uri
}

output "db_connection_name" {
  description = "Cloud SQL connection name (use as CLOUD_SQL_INSTANCE)"
  value       = google_sql_database_instance.main.connection_name
}

output "db_public_ip" {
  description = "Cloud SQL public IP"
  value       = google_sql_database_instance.main.public_ip_address
}

output "gcs_bucket_raw" {
  description = "GCS bucket for raw files"
  value       = google_storage_bucket.radar_raw.name
}

output "pubsub_collect_trigger" {
  description = "Pub/Sub topic for collection trigger"
  value       = google_pubsub_topic.collect_trigger.id
}

output "pubsub_property_events" {
  description = "Pub/Sub topic for property events"
  value       = google_pubsub_topic.property_events.id
}

output "wif_provider" {
  description = "Workload Identity Provider (use in deploy.yml WIF_PROVIDER)"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "github_actions_sa" {
  description = "GitHub Actions service account email (use in deploy.yml SERVICE_ACCOUNT)"
  value       = google_service_account.github_actions.email
}
