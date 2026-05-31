resource "google_secret_manager_secret" "db_url" {
  secret_id = "radar-db-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_url" {
  secret = google_secret_manager_secret.db_url.id
  secret_data = (
    "postgresql+pg8000://radar_app:${var.db_password}@/${google_sql_database.radar.name}"
    "?unix_sock=/cloudsql/${google_sql_database_instance.main.connection_name}/.s.PGSQL.5432"
  )
}

resource "google_secret_manager_secret" "telegram_token" {
  secret_id = "radar-telegram-token"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "telegram_token" {
  secret      = google_secret_manager_secret.telegram_token.id
  secret_data = var.telegram_bot_token
}

resource "google_secret_manager_secret" "firebase_creds" {
  secret_id = "radar-firebase-creds"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "firebase_creds" {
  secret      = google_secret_manager_secret.firebase_creds.id
  secret_data = var.firebase_credentials_json
}
