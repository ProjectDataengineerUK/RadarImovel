resource "google_pubsub_topic" "collect_trigger" {
  name = "collect-trigger"
}

resource "google_pubsub_topic" "property_events" {
  name = "property-events"
}

resource "google_pubsub_topic" "property_events_dlq" {
  name = "property-events-dlq"
}

resource "google_pubsub_subscription" "property_events_sub" {
  name  = "property-events-sub"
  topic = google_pubsub_topic.property_events.name

  ack_deadline_seconds = 60
  message_retention_duration = "86400s"  # 24h

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.property_events_dlq.id
    max_delivery_attempts = 5
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }
}
