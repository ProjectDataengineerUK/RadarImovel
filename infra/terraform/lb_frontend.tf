locals {
  domain     = "mastavista.com.br"
  domain_www = "www.mastavista.com.br"
}

# ── APIs necessárias ──────────────────────────────────────────────────────────

resource "google_project_service" "compute" {
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

# ── IP global estático ────────────────────────────────────────────────────────

resource "google_compute_global_address" "frontend" {
  name = "radar-frontend-ip"

  depends_on = [google_project_service.compute]
}

# ── Serverless NEG → Cloud Run frontend ──────────────────────────────────────

resource "google_compute_region_network_endpoint_group" "frontend" {
  name                  = "radar-frontend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  cloud_run {
    service = google_cloud_run_v2_service.frontend.name
  }

  depends_on = [google_project_service.compute]
}

# ── Backend service ───────────────────────────────────────────────────────────

resource "google_compute_backend_service" "frontend" {
  name                  = "radar-frontend-backend"
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  enable_cdn            = true

  cdn_policy {
    cache_mode                   = "CACHE_ALL_STATIC"
    default_ttl                  = 3600
    client_ttl                   = 3600
    max_ttl                      = 86400
    negative_caching             = true
    serve_while_stale            = 86400
  }

  backend {
    group = google_compute_region_network_endpoint_group.frontend.id
  }

  depends_on = [google_project_service.compute]
}

# ── SSL gerenciado pelo Google ────────────────────────────────────────────────

resource "google_compute_managed_ssl_certificate" "frontend" {
  name = "radar-frontend-ssl"

  managed {
    domains = [local.domain, local.domain_www]
  }

  depends_on = [google_project_service.compute]
}

# ── URL map: redireciona www → apex ──────────────────────────────────────────

resource "google_compute_url_map" "frontend" {
  name            = "radar-frontend-urlmap"
  default_service = google_compute_backend_service.frontend.id

  host_rule {
    hosts        = [local.domain_www]
    path_matcher = "www-redirect"
  }

  path_matcher {
    name            = "www-redirect"
    default_url_redirect {
      host_redirect          = local.domain
      redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
      strip_query            = false
    }
  }

  depends_on = [google_project_service.compute]
}

# ── URL map HTTP → redireciona tudo para HTTPS ───────────────────────────────

resource "google_compute_url_map" "http_redirect" {
  name = "radar-frontend-http-redirect"

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }

  depends_on = [google_project_service.compute]
}

# ── HTTPS proxy ───────────────────────────────────────────────────────────────

resource "google_compute_target_https_proxy" "frontend" {
  name             = "radar-frontend-https-proxy"
  url_map          = google_compute_url_map.frontend.id
  ssl_certificates = [google_compute_managed_ssl_certificate.frontend.id]

  depends_on = [google_project_service.compute]
}

# ── HTTP proxy (só redireciona para HTTPS) ────────────────────────────────────

resource "google_compute_target_http_proxy" "frontend" {
  name    = "radar-frontend-http-proxy"
  url_map = google_compute_url_map.http_redirect.id

  depends_on = [google_project_service.compute]
}

# ── Forwarding rules ──────────────────────────────────────────────────────────

resource "google_compute_global_forwarding_rule" "https" {
  name                  = "radar-frontend-https"
  target                = google_compute_target_https_proxy.frontend.id
  port_range            = "443"
  ip_address            = google_compute_global_address.frontend.id
  load_balancing_scheme = "EXTERNAL_MANAGED"

  depends_on = [google_project_service.compute]
}

resource "google_compute_global_forwarding_rule" "http" {
  name                  = "radar-frontend-http"
  target                = google_compute_target_http_proxy.frontend.id
  port_range            = "80"
  ip_address            = google_compute_global_address.frontend.id
  load_balancing_scheme = "EXTERNAL_MANAGED"

  depends_on = [google_project_service.compute]
}

# ── Outputs ───────────────────────────────────────────────────────────────────

output "lb_ip" {
  description = "IP do Load Balancer — use este valor como registro A no DNS do domínio"
  value       = google_compute_global_address.frontend.address
}

output "frontend_domain" {
  description = "Domínio configurado"
  value       = "https://${local.domain}"
}
