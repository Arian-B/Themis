variable "project_id" {
  description = "GCP project ID (or AWS account ID) for the deployment target."
  type        = string
}

variable "region" {
  description = "Primary deployment region."
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name: staging | production"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be 'staging' or 'production'."
  }
}

variable "neo4j_password" {
  description = "Neo4j admin password. Source from secrets manager, not tfvars."
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key for Claude. Source from secrets manager."
  type        = string
  sensitive   = true
}
