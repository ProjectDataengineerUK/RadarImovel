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
  description = "Cloud SQL PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "telegram_bot_token" {
  description = "Telegram Bot API token"
  type        = string
  sensitive   = true
}

variable "firebase_credentials_json" {
  description = "Firebase service account JSON"
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "api_image" {
  description = "Docker image for the API (Cloud Run)"
  type        = string
}

variable "job_image" {
  description = "Docker image for Cloud Run Jobs"
  type        = string
}
