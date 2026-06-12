resource "google_secret_manager_secret" "db_password" {
  secret_id = "db_password"
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}

resource "google_secret_manager_secret" "telegram_bot_token" {
  secret_id = "telegram_bot_token"
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "telegram_bot_token" {
  secret      = google_secret_manager_secret.telegram_bot_token.id
  secret_data = var.telegram_bot_token
}

resource "google_secret_manager_secret" "firebase_credentials_json" {
  secret_id = "firebase_credentials_json"
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "firebase_credentials_json" {
  secret      = google_secret_manager_secret.firebase_credentials_json.id
  secret_data = var.firebase_credentials_json
}

# ── Onda 2: canais adicionais ────────────────────────────────────────────────

resource "google_secret_manager_secret" "whatsapp_access_token" {
  secret_id = "whatsapp_access_token"
  replication { auto {} }
}

resource "google_secret_manager_secret" "sendgrid_api_key" {
  secret_id = "sendgrid_api_key"
  replication { auto {} }
}

resource "google_secret_manager_secret" "fcm_access_token" {
  secret_id = "fcm_access_token"
  replication { auto {} }
}
