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

  ack_deadline_seconds       = 60
  message_retention_duration = "86400s" # 24h

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.property_events_dlq.id
    max_delivery_attempts = 5
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }
}

# ── Fase 2: processamento de editais ────────────────────────────────────────

resource "google_pubsub_topic" "edital_events" {
  name = "edital-events"
}

resource "google_pubsub_topic" "edital_events_dlq" {
  name = "edital-events-dlq"
}

resource "google_pubsub_subscription" "edital_events_sub" {
  name  = "edital-events-sub"
  topic = google_pubsub_topic.edital_events.name

  ack_deadline_seconds       = 120 # Gemini P95 < 60s + margem
  message_retention_duration = "86400s"

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.edital_events_dlq.id
    max_delivery_attempts = 5
  }

  retry_policy {
    minimum_backoff = "30s"
    maximum_backoff = "600s"
  }
}
