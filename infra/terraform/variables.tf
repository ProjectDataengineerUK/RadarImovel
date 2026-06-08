variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "db_password" {
  description = "Cloud SQL password for the radar_app user"
  type        = string
  sensitive   = true
}

variable "telegram_bot_token" {
  description = "Telegram Bot API token"
  type        = string
  sensitive   = true
}

variable "firebase_credentials_json" {
  description = "Firebase service account JSON (entire file content)"
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "github_repo" {
  description = "GitHub repo in owner/name format (e.g. ProjectDataengineerUK/RadarImovel)"
  type        = string
}

# ── Fase 2: Vertex AI / editais ─────────────────────────────────────────────

variable "vertex_location" {
  description = "Região do Vertex AI (Gemini)"
  type        = string
  default     = "us-central1"
}

variable "gemini_model" {
  description = "Modelo Gemini default para extração de editais"
  type        = string
  default     = "gemini-2.0-flash"
}

variable "gcs_bucket_docs" {
  description = "Bucket dos PDFs de editais (prefix editais/)"
  type        = string
  default     = "radar-imovel-docs"
}
