# =============================================================================
# Themis — Terraform main configuration
# Phase 6 implementation target. Currently a documented skeleton.
#
# Architecture provisioned:
#   - GKE Autopilot cluster (or EKS — swap provider block)
#   - VPC with private subnets for data services
#   - Cloud SQL (PostgreSQL) for LangGraph checkpointing + correction records
#   - Secret Manager entries for all sensitive env vars
#   - Cloud Armor WAF for API ingress (production only)
#   - GCS bucket for PDF uploads + model artifacts
# =============================================================================

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # TODO (Phase 6): Configure GCS remote state backend
  # backend "gcs" {
  #   bucket = "themis-terraform-state"
  #   prefix = "terraform/state"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# TODO (Phase 6): Implement the following resources:
# resource "google_container_cluster" "themis" { ... }      # GKE Autopilot
# resource "google_sql_database_instance" "postgres" { ... } # Cloud SQL
# resource "google_secret_manager_secret" "secrets" { ... }  # Secret Manager
# resource "google_storage_bucket" "uploads" { ... }          # PDF storage
# resource "google_compute_security_policy" "waf" { ... }     # Cloud Armor
