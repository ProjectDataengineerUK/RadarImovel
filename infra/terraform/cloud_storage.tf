resource "google_storage_bucket" "radar_raw" {
  name          = "radar-raw-${var.project_id}"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 365 }  # arquivos brutos deletados após 1 ano
  }

  versioning {
    enabled = false
  }
}
