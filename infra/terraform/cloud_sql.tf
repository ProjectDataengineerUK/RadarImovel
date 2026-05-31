resource "google_sql_database_instance" "main" {
  name             = "radar-imovel-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = "db-f1-micro"  # shared-core — suficiente para MVP
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

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.default.id
    }
  }

  deletion_protection = true
  depends_on          = [google_project_service.apis]
}

resource "google_sql_database" "radar" {
  name     = "radar_imovel"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app" {
  name     = "radar_app"
  instance = google_sql_database_instance.main.name
  password = var.db_password
}

resource "google_compute_network" "default" {
  name                    = "radar-imovel-vpc"
  auto_create_subnetworks = true
}

resource "google_compute_global_address" "private_ip_range" {
  name          = "radar-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.default.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.default.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
}
