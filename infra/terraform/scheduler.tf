locals {
  ufs = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
    "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
    "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
  ]
  # 3 disparos por dia: 08h, 14h, 20h (horário de Brasília = UTC-3)
  schedules = ["0 11 * * *", "0 17 * * *", "0 23 * * *"]
}

resource "google_cloud_scheduler_job" "collect_caixa" {
  for_each = toset(local.schedules)

  name      = "collect-caixa-${replace(each.key, " ", "-")}"
  schedule  = each.key
  time_zone = "UTC"

  pubsub_target {
    topic_name = google_pubsub_topic.collect_trigger.id
    data = base64encode(jsonencode({
      bank = "caixa"
      ufs  = local.ufs
    }))
  }
}

# ── Fase 3: schedulers por banco habilitado (var.enabled_banks) ──────────────
# Cada banco (exceto caixa, já coberto acima) coleta de forma nacional.
# Produto cartesiano banco × horário.
locals {
  fase3_banks = setsubtract(toset(var.enabled_banks), toset(["caixa"]))
  bank_schedule_pairs = {
    for pair in setproduct(tolist(local.fase3_banks), local.schedules) :
    "${pair[0]}-${replace(pair[1], " ", "-")}" => { bank = pair[0], cron = pair[1] }
  }
}

resource "google_cloud_scheduler_job" "collect_bank" {
  for_each = local.bank_schedule_pairs

  name      = "collect-${each.value.bank}-${replace(each.value.cron, " ", "-")}"
  schedule  = each.value.cron
  time_zone = "UTC"

  pubsub_target {
    topic_name = google_pubsub_topic.collect_trigger.id
    data = base64encode(jsonencode({
      bank = each.value.bank
      ufs  = []
    }))
  }
}
