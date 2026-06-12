# Vertex AI Vector Search para RAG sobre editais e matrículas

resource "google_vertex_ai_index" "rag_editais" {
  region       = var.region
  display_name = "radar-imovel-rag-editais"
  description  = "Índice vetorial para chunks de editais e matrículas (RAG)"

  metadata {
    contents_delta_uri = "gs://${google_storage_bucket.docs.name}/rag/index_data/"
    config {
      dimensions                  = 768
      approximate_neighbors_count = 150
      distance_measure_type       = "DOT_PRODUCT_DISTANCE"
      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count    = 1000
          leaf_nodes_to_search_percent = 10
        }
      }
    }
  }

  index_update_method = "STREAM_UPDATE"
}

resource "google_vertex_ai_index_endpoint" "rag_editais" {
  region       = var.region
  display_name = "radar-imovel-rag-endpoint"
  description  = "Endpoint para consultas RAG ao Vertex AI Vector Search"

  depends_on = [google_vertex_ai_index.rag_editais]
}

output "vertex_index_id" {
  value       = google_vertex_ai_index.rag_editais.id
  description = "ID do Vertex AI Index para RAG"
}

output "vertex_index_endpoint_id" {
  value       = google_vertex_ai_index_endpoint.rag_editais.id
  description = "ID do Vertex AI Index Endpoint para RAG"
}
