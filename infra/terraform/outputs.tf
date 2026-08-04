output "gke_cluster_endpoint" {
  description = "GKE cluster API server endpoint for kubectl configuration."
  value       = "TODO: google_container_cluster.themis.endpoint"
  sensitive   = true
}

output "api_service_url" {
  description = "External URL of the Themis API (after Ingress + DNS setup)."
  value       = "TODO: provisioned after Phase 6 implementation"
}
