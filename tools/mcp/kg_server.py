"""
tools/mcp/kg_server.py — MCP server exposing knowledge graph write/query tools.

Tools exposed by this server:
  1. write_entity(entity: dict, tenant_id: str) → str (entity_id)
     Writes a node to Neo4j via graph_store.write_entity() (MERGE semantics).

  2. write_relationship(rel: dict, tenant_id: str) → None
     Writes an edge to Neo4j via graph_store.write_relationship() (MERGE semantics).

  3. query_portfolio(cypher: str, tenant_id: str, params: dict) → list[dict]
     Executes a read-only Cypher query for portfolio aggregation.
     Example: "Find all contracts with HIGH risk obligations due in 30 days"

  4. get_obligations_due(tenant_id: str, days_ahead: int) → list[dict]
     Convenience query for n8n deadline reminder workflow.

Why separate from retrieval_server?
  Write operations to Neo4j are security-sensitive (wrong write = data corruption).
  Keeping them in a separate MCP server allows different auth/rate-limit policies.
"""

from __future__ import annotations

# TODO (Phase 3b): Implement using MCP Python SDK.
# See retrieval_server.py for the Server pattern to follow.

raise NotImplementedError("Phase 3b: kg_server MCP server not yet implemented")
