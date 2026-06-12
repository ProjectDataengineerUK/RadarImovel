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

variable "enabled_banks" {
  description = "Bancos com coleta agendada (devem ter active=true em banks e connector validado)"
  type        = list(string)
  default     = ["caixa", "bb", "brb", "bnb", "basa", "banrisul", "banestes"]
}

variable "bank_request_delay_ms" {
  description = "Delay padrão entre requisições por banco (ms), respeito a servidores públicos"
  type        = number
  default     = 1000
}

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

# ── Mapa de Risco ────────────────────────────────────────────────────────────

variable "risk_score_change_threshold" {
  description = "Pontos mínimos de variação para publicar risk-change-events"
  type        = number
  default     = 10
}

variable "risk_job_enabled" {
  description = "Habilita o job radar-calculate-risk"
  type        = bool
  default     = true
}

variable "gcs_bucket_docs" {
  description = "Bucket dos PDFs de editais (prefix editais/)"
  type        = string
  default     = "radar-imovel-docs"
}
