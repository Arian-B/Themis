"""
agents/knowledge_graph_writer.py — Agent 5: Knowledge Graph Writer Agent.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import uuid
from typing import Any
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from graph.state import ThemisState
from schemas.knowledge_graph import GraphEntity, GraphRelationship, KGWriteResult
from utils.llm_provider import get_complex_reasoning_llm
from utils.mcp_client import call_mcp_tool

logger = logging.getLogger(__name__)

class GraphEntityExtracted(BaseModel):
    entity_id: str
    entity_type: str = Field(description="Must be one of: party, obligation, date, counterparty, clause_reference")
    name: str

class GraphRelationshipExtracted(BaseModel):
    from_entity_id: str
    to_entity_id: str
    relationship_type: str = Field(
        alias="type", 
        default="RELATED_TO",
        description="The specific type of relationship, e.g., 'obligated_by', 'references', 'expires_on', 'party_to', 'governs', 'amends'."
    )

class KGDraft(BaseModel):
    entities: list[GraphEntityExtracted] = Field(description="List of entities extracted from the contract.")
    relationships: list[GraphRelationshipExtracted] = Field(description="List of relationships between extracted entities.")

_SYSTEM_PROMPT = """\
You are an expert legal ontologist. You will be provided with a contract's extracted clauses and verified risk flags.
Your task is to extract a knowledge graph representing the key entities and relationships.

Important:
- Use clear, consistent names for entities.
- Assign meaningful `relationship_type` values (e.g., "party_to", "obligated_by", "expires_on", "references", "governs") based on how the entities connect. Do NOT just use generic types like "RELATED_TO".
- Ensure every `from_entity_id` and `to_entity_id` in a relationship EXACTLY matches an `entity_id` of an extracted entity in your response.
- You MUST respond in JSON format, exactly matching this JSON schema:
{schema}
"""

def extract_and_write_kg(state: ThemisState) -> dict[str, Any]:
    """
    LangGraph node: Extract KG and write to Neo4j via MCP.
    """
    contract_id = state.get("contract_id", str(uuid.uuid4()))
    tenant_id = state.get("tenant_id", "default_tenant")
    ext_result = state.get("extraction_result")
    ver_result = state.get("verification_result", [])
    
    if not ext_result or not ext_result.get("clauses"):
        logger.warning("knowledge_graph_writer: No extraction result found in state.")
        return {}

    llm = get_complex_reasoning_llm(temperature=0).with_structured_output(KGDraft, method="json_mode")

    clauses_text = "\n".join([f"Clause ID: {c.get('clause_id')} - Type: {c.get('clause_type')}\nText: {c.get('text')}" for c in ext_result["clauses"]])
    flags_text = "\n".join([f"Flag on Clause {f.get('clause_id')}: {f.get('concern')}" for f in ver_result if f.get('verified')])

    prompt_text = f"CONTRACT ID: {contract_id}\n\nCLAUSES:\n{clauses_text}\n\nVERIFIED FLAGS:\n{flags_text}"

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT.format(schema=json.dumps(KGDraft.model_json_schema(), indent=2))),
        HumanMessage(content=prompt_text)
    ]

    errors: list[dict[str, Any]] = list(state.get("errors") or [])
    
    try:
        draft = llm.invoke(messages)
    except Exception as e:
        logger.error(f"knowledge_graph_writer: LLM extraction failed: {e}")
        errors.append({
            "node": "knowledge_graph_writer",
            "error_type": "LLMError",
            "message": str(e),
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
        })
        return {"errors": errors}

    # Call MCP to write to Neo4j
    mcp_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools", "mcp", "knowledge_graph_server.py"))
    
    valid_types = {"party", "obligation", "date", "counterparty", "clause_reference"}
    final_entities = []
    for e in draft.entities:
        e_type = e.entity_type.lower()
        if e_type not in valid_types:
            e_type = "clause_reference"
        final_entities.append(GraphEntity(
            entity_id=e.entity_id,
            entity_type=e_type,
            name=e.name,
            contract_id=contract_id
        ))
        
    final_relationships = []
    for r in draft.relationships:
        final_relationships.append(GraphRelationship(
            from_entity_id=r.from_entity_id,
            to_entity_id=r.to_entity_id,
            relationship_type=r.relationship_type,
            contract_id=contract_id
        ))

    ents_dicts = [e.model_dump() for e in final_entities]
    rels_dicts = [r.model_dump() for r in final_relationships]

    write_errors = []
    try:
        response_json = call_mcp_tool(mcp_script, "write_to_neo4j", {"entities": ents_dicts, "relationships": rels_dicts})
        resp = json.loads(response_json)
        if resp.get("status") == "error":
            write_errors.append(resp.get("message"))
    except Exception as e:
        logger.error(f"knowledge_graph_writer: MCP call failed: {e}")
        write_errors.append(str(e))

    kg_write_result = KGWriteResult(
        contract_id=contract_id,
        tenant_id=tenant_id,
        entities_written=len(ents_dicts) if not write_errors else 0,
        relationships_written=len(rels_dicts) if not write_errors else 0,
        entities=final_entities,
        relationships=final_relationships,
        write_errors=write_errors
    )

    return {
        "kg_write_result": kg_write_result.model_dump(),
        **({"errors": errors} if errors else {})
    }
