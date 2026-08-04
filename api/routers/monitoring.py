"""
api/routers/monitoring.py — Regulatory monitoring endpoints.

These endpoints expose the Regulatory Monitoring Agent's output to the frontend
and to n8n automation workflows.

Endpoints:
  GET /api/v1/regulatory-alerts
    Returns list of active RegulatoryAlert objects for the authenticated tenant.
    Supports filtering: ?impact_level=high&contract_id=<uuid>&unresolved_only=true
    Consumed by: React frontend alert banner + n8n alert digest workflow.

  POST /api/v1/regulatory-alerts/{alert_id}/resolve
    Marks an alert as resolved (human-reviewed and actioned).
    Records a CorrectionRecord if the alert was a false positive.

  GET /api/v1/regulations/tracked
    Lists all Regulation nodes tracked for this tenant (from Neo4j).
    Allows tenants to see what regulatory sources Themis monitors for them.

  POST /api/v1/regulations/track
    Registers a new regulation URL for monitoring.
    Body: {jurisdiction, title, source_url}
    Creates a Regulation node in Neo4j; picked up by monitoring agent on next run.

  POST /api/v1/monitoring/trigger
    Manually triggers a regulatory monitoring run for this tenant.
    Useful for testing without waiting for the n8n cron schedule.
    Restricted to admin users (role claim in JWT).

n8n integration:
  n8n's "regulatory_alert_digest" workflow polls GET /regulatory-alerts daily.
  n8n's "high_risk_escalation" workflow is triggered by a webhook fired by
  the Regulatory Monitoring Agent when impact_level == CRITICAL.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from api.dependencies import TenantContext, get_current_tenant

router = APIRouter(prefix="/regulatory", tags=["monitoring"])

# TODO (Phase 4): Implement all endpoints.
