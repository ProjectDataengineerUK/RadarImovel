resource "google_sql_database_instance" "main" {
  name             = "radar-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    disk_size         = 10
    disk_type         = "PD_SSD"

    database_flags {
      name  = "max_connections"
      value = "100"
    }

    backup_configuration {
      enabled    = true
      start_time = "03:00"
    }

    # Public IP required for Cloud SQL Python Connector from Cloud Run (no VPC connector)
    ip_configuration {
      ipv4_enabled = true
      require_ssl  = true
    }
  }

  deletion_protection = true
  depends_on          = [google_project_service.apis]
}

resource "google_sql_database" "radar" {
  name     = "radar"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app" {
  name     = "radar_app"
  instance = google_sql_database_instance.main.name
  password = var.db_password
}
