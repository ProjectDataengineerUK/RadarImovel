output "api_url" {
  description = "Cloud Run API URL"
  value       = google_cloud_run_v2_service.api.uri
}

output "db_connection_name" {
  description = "Cloud SQL connection name"
  value       = google_sql_database_instance.main.connection_name
}

output "db_private_ip" {
  description = "Cloud SQL private IP"
  value       = google_sql_database_instance.main.private_ip_address
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
