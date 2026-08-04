"""
api/routers/portfolio.py — Portfolio aggregation endpoints.

These endpoints power the React Portfolio Risk Heatmap. They query the Neo4j
knowledge graph (via MCP kg_server) to produce cross-document risk summaries
for a tenant's entire contract portfolio.

Endpoints:
  GET /api/v1/portfolio/heatmap
    Returns a 2D grid: contracts (rows) × risk dimensions (columns), each cell
    containing a RiskLevel colour value. Consumed directly by the React heatmap
    component.
    Query params: ?jurisdiction=us_generic&risk_level_min=medium

  GET /api/v1/portfolio/obligations
    Lists all obligations across the portfolio with due dates.
    Supports ?days_ahead=30 for deadline-aware filtering.
    Powers the n8n deadline reminder workflow (n8n polls this).

  GET /api/v1/portfolio/counterparties
    Graph-powered: returns all Party nodes + their associated contracts.
    Enables "show me all contracts with vendor X" queries.

  GET /api/v1/portfolio/summary
    Aggregate stats: total contracts, risk distribution, jurisdiction breakdown.
    Used for the dashboard overview card.

Multi-tenancy:
  All queries include tenant_id from TenantContext (JWT-derived).
  No cross-tenant data is ever returned.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from api.dependencies import TenantContext, get_current_tenant

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# TODO (Phase 4): Implement all endpoints.
# Each calls graph_store.query_portfolio() via MCP kg_server.query_portfolio tool.
