locals {
  ufs = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
    "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
    "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
  ]
  # 3 disparos por dia: 08h, 14h, 20h (horário de Brasília = UTC-3)
  schedules = ["0 11 * * *", "0 17 * * *", "0 23 * * *"]

  jobs_api_base = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs"
}

# Caixa: 3 execuções diárias do job radar-collect-caixa (processa os 27 UFs em sequência)
resource "google_cloud_scheduler_job" "collect_caixa" {
  for_each = toset(local.schedules)

  name             = "collect-caixa-${replace(each.key, " ", "-")}"
  schedule         = each.key
  time_zone        = "UTC"
  attempt_deadline = "3600s"

  http_target {
    http_method = "POST"
    uri         = "${local.jobs_api_base}/radar-collect-caixa:run"
    body        = base64encode("{}")

    oauth_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }
}

# ── Fase 3: schedulers por banco habilitado (var.enabled_banks) ──────────────
locals {
  fase3_banks = setsubtract(toset(var.enabled_banks), toset(["caixa"]))
  bank_schedule_pairs = {
    for pair in setproduct(tolist(local.fase3_banks), local.schedules) :
    "${pair[0]}-${replace(pair[1], " ", "-")}" => { bank = pair[0], cron = pair[1] }
  }
}

# ── Onda 1: expire subscriptions diariamente às 01h UTC ──────────────────────
resource "google_cloud_scheduler_job" "expire_subscriptions" {
  name             = "expire-subscriptions"
  schedule         = "0 1 * * *"
  time_zone        = "UTC"
  attempt_deadline = "300s"

  http_target {
    http_method = "POST"
    uri         = "${local.jobs_api_base}/radar-expire-subscriptions:run"
    body        = base64encode("{}")

    oauth_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }
}

resource "google_cloud_scheduler_job" "collect_bank" {
  for_each = local.bank_schedule_pairs

  name             = "collect-${each.value.bank}-${replace(each.value.cron, " ", "-")}"
  schedule         = each.value.cron
  time_zone        = "UTC"
  attempt_deadline = "3600s"

  http_target {
    http_method = "POST"
    uri         = "${local.jobs_api_base}/radar-collect-bank:run"
    body = base64encode(jsonencode({
      overrides = {
        containerOverrides = [{
          env = [{ name = "BANK", value = each.value.bank }]
        }]
      }
    }))

    oauth_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }
}

# ── Onda 3: schedulers por leiloeiro (SOURCE_REGISTRY) ───────────────────────
# tos_compliant=false por padrão → job bloqueia até FORCE_TOS=true ser definido
# após validação jurídica individual de cada ToS
locals {
  auctioneers = ["zuk", "mega", "sodre", "fidalgo", "frazao"]
  # Leiloeiros: 2 disparos/dia (menos frequente que bancos)
  auctioneer_schedules = ["0 12 * * *", "0 20 * * *"]
  auctioneer_schedule_pairs = {
    for pair in setproduct(local.auctioneers, local.auctioneer_schedules) :
    "${pair[0]}-${replace(pair[1], " ", "-")}" => { source = pair[0], cron = pair[1] }
  }
}

resource "google_cloud_scheduler_job" "collect_source" {
  for_each = local.auctioneer_schedule_pairs

  name             = "collect-${each.value.source}-${replace(each.value.cron, " ", "-")}"
  schedule         = each.value.cron
  time_zone        = "UTC"
  attempt_deadline = "3600s"

  http_target {
    http_method = "POST"
    uri         = "${local.jobs_api_base}/radar-collect-source:run"
    body = base64encode(jsonencode({
      overrides = {
        containerOverrides = [{
          env = [{ name = "SOURCE", value = each.value.source }]
        }]
      }
    }))

    oauth_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }
}
