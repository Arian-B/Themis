"""
tools/mcp/retrieval_server.py — MCP server exposing retrieval tools to agent nodes.
"""

import json
import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path if not already there
ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP
from retrieval.qdrant_retriever import get_retriever

logger = logging.getLogger(__name__)

mcp = FastMCP("themis-retrieval")

@mcp.tool()
def search_corpus(query: str, jurisdiction: str, k: int = 3) -> str:
    """
    Search the statute corpus for historical precedent or applicable law.
    
    Args:
        query: The semantic search query.
        jurisdiction: The jurisdiction (e.g. 'us_generic' or 'uk').
        k: The number of results to retrieve.
        
    Returns:
        JSON string containing a list of matched documents.
    """
    retriever = get_retriever(jurisdiction=jurisdiction, k=k)
    if not retriever:
        return json.dumps({"error": f"Could not initialize retriever for jurisdiction: {jurisdiction}"})
    
    # Run the retrieval
    try:
        results = []
        vs = getattr(retriever, "vectorstore", None)
        if vs and hasattr(vs, "similarity_search_with_score"):
            docs_and_scores = vs.similarity_search_with_score(query, k=k)
            for doc, score in docs_and_scores:
                doc_id = str(doc.metadata.get("_id") or doc.metadata.get("id") or getattr(doc, "id", None) or "unknown_id")
                res = {
                    "id": doc_id,
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                }
                results.append(res)
        else:
            docs = retriever.invoke(query)
            for doc in docs:
                doc_id = str(doc.metadata.get("_id") or doc.metadata.get("id") or getattr(doc, "id", None) or "unknown_id")
                score = doc.metadata.get("score")
                res = {
                    "id": doc_id,
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                if score is not None:
                    res["score"] = score
                results.append(res)
            
        return json.dumps(results)
    except Exception as e:
        logger.error(f"search_corpus error: {e}")
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_contract_clauses(contract_id: str) -> str:
    """
    Fetch the complete set of extracted clauses for a given contract.
    Used for full-contract cross-clause verification.
    
    Args:
        contract_id: The unique ID of the contract.
        
    Returns:
        JSON string containing the extraction result (list of clauses) or error.
    """
    runtime_dir = ROOT / "data" / "runtime"
    cache_path = runtime_dir / f"extraction_{contract_id}.json"
    
    if not cache_path.exists():
        return json.dumps({
            "error": f"Extracted clauses for contract_id '{contract_id}' not found.",
            "clauses": []
        })
        
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        return json.dumps(data)
    except Exception as e:
        logger.error(f"Error reading cache for contract {contract_id}: {e}")
        return json.dumps({"error": str(e), "clauses": []})

if __name__ == "__main__":
    mcp.run()
