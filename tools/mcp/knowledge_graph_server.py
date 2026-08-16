"""
tools/mcp/knowledge_graph_server.py — MCP server exposing Neo4j operations to agent nodes.
"""

import json
import logging
import os
import sys
import re
from pathlib import Path

# Add project root to sys.path if not already there
ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

mcp = FastMCP("themis-knowledge-graph")

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "arianbNeo4j")  # Fallback to local password

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def _sanitize_label(label: str) -> str:
    """Ensure label is safe for Cypher query injection."""
    clean = re.sub(r'[^a-zA-Z0-9_]', '', str(label))
    return clean.capitalize()

def _sanitize_rel_type(rel_type: str) -> str:
    """Ensure relationship type is safe for Cypher query injection."""
    clean = re.sub(r'[^a-zA-Z0-9_]', '', str(rel_type).replace(" ", " _"))
    return clean.upper()


@mcp.tool()
def write_to_neo4j(entities: list[dict], relationships: list[dict]) -> str:
    """
    Write a list of entities and relationships to Neo4j.
    
    Args:
        entities: List of dicts matching GraphEntity schema.
        relationships: List of dicts matching GraphRelationship schema.
        
    Returns:
        JSON string indicating success.
    """
    def _create_nodes_and_edges(tx, ents, rels):
        # Merge entities
        for ent in ents:
            label = _sanitize_label(ent.get("entity_type", "Entity"))
            query = f"""
            MERGE (n:{label} {{entity_id: $id}})
            ON CREATE SET n.name = $name, n.contract_id = $contract_id, n.entity_type = $entity_type
            ON MATCH SET n.name = $name, n.contract_id = $contract_id, n.entity_type = $entity_type
            """
            tx.run(query, id=ent["entity_id"], name=ent["name"], contract_id=ent["contract_id"], entity_type=ent["entity_type"])
            
        # Merge relationships
        for rel in rels:
            from_id = rel["from_entity_id"]
            to_id = rel["to_entity_id"]
            rel_type = _sanitize_rel_type(rel.get("relationship_type", "RELATED_TO"))
            query = f"""
            MATCH (a {{entity_id: $from_id}})
            MATCH (b {{entity_id: $to_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            ON CREATE SET r.contract_id = $contract_id
            ON MATCH SET r.contract_id = $contract_id
            """
            tx.run(query, from_id=from_id, to_id=to_id, contract_id=rel.get("contract_id", ""))
            
    try:
        with driver.session() as session:
            session.execute_write(_create_nodes_and_edges, entities, relationships)
        return json.dumps({
            "status": "success", 
            "message": f"Successfully wrote {len(entities)} entities and {len(relationships)} relationships to Neo4j."
        })
    except Exception as e:
        logger.error(f"Failed to write to Neo4j: {e}")
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def query_counterparty_auto_renewal(counterparty_name: str) -> str:
    """
    Execute a cross-document query to find all contracts involving the given counterparty 
    and flag any containing an auto_renewal clause.
    
    Args:
        counterparty_name: The name of the counterparty to search for.
        
    Returns:
        JSON string containing matching paths.
    """
    query = """
    MATCH (cp)
    WHERE cp.name =~ '(?i).*' + $name + '.*' AND cp.entity_type IN ['party', 'counterparty']
    MATCH (cp)-[*1..3]-(c)
    WHERE c.name =~ '(?i).*auto.*renewal.*' OR c.entity_type = 'clause_reference' AND c.name =~ '(?i).*auto.*'
    RETURN DISTINCT cp.name AS counterparty, c.contract_id AS contract_id, c.name AS clause_name, labels(c) AS clause_labels
    """
    try:
        with driver.session() as session:
            result = session.run(query, name=counterparty_name)
            records = [dict(record) for record in result]
        return json.dumps({
            "status": "success",
            "matches": records
        })
    except Exception as e:
        logger.error(f"Failed to query Neo4j: {e}")
        return json.dumps({"status": "error", "message": str(e)})

if __name__ == "__main__":
    mcp.run()
