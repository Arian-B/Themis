"""
agents/kg_writer.py — Agent 5: Knowledge Graph Writer.

Responsibility:
  Extracts legal entities and relationships from state["clause_bundle"] and
  writes them to the Neo4j knowledge graph via the MCP kg_server. This
  enables cross-document portfolio queries and regulatory monitoring.

Entity types (defined in schemas/knowledge_graph.py):
  - Party      (name, type: [vendor|client|counterparty], jurisdiction)
  - Obligation (text, obligor, obligee, deadline: Optional[date])
  - Contract   (id, title, tenant_id, upload_date, jurisdiction)
  - Clause     (id, contract_id, clause_type, text_hash)
  - Regulation (id, jurisdiction, title, effective_date, source_url)

Relationship types:
  - Party     -[PARTY_TO]→    Contract
  - Contract  -[CONTAINS]→    Clause
  - Clause    -[CREATES]→     Obligation
  - Obligation -[DUE_BY]→     date node (or inline property)
  - Contract  -[GOVERNED_BY]→ Regulation (set by Regulatory Monitoring Agent)

Multi-tenant isolation:
  All nodes are tagged with tenant_id property. Neo4j queries from this agent
  always include WHERE n.tenant_id = $tenant_id to prevent cross-tenant leakage.

Output: state["kg_write_result"] = KGWriteResult.model_dump()
"""

from __future__ import annotations

from typing import Any, ClassVar

from agents.base_agent import BaseAgent
from graph.state import ThemisState
from schemas.knowledge_graph import KGWriteResult

# TODO (Phase 3b): Implement _run():
#   1. Deserialise state["clause_bundle"] into ClauseBundle
#   2. Use Claude/Ollama to extract entities and relationships from each clause
#   3. Call MCP kg_server write_entity() and write_relationship() for each
#   4. All writes tagged with state["tenant_id"]
#   5. Return {"kg_write_result": result.model_dump()}


class KGWriterAgent(BaseAgent):
    node_name: ClassVar[str] = "kg_writer"
    output_schema: ClassVar[type[KGWriteResult]] = KGWriteResult

    async def _run(self, state: ThemisState) -> dict[str, Any]:
        raise NotImplementedError("Phase 3b: KGWriterAgent._run() not implemented")
