"""
agents/jurisdiction_classifier.py — Agent 1: Jurisdiction Classifier.

Responsibility:
  Reads state["raw_text"] (a small prefix/header of the contract), calls a local
  Ollama model (cheap inference) to classify the governing-law jurisdiction, and
  writes the result to state["jurisdiction_result"] as a serialised JurisdictionResult.

Model strategy:
  - Uses Ollama with a small local model (llama3.2:3b or llama3.1:8b).
  - Structured output enforced via PydanticAI — the LLM must produce a JSON
    object matching JurisdictionResult or the call is retried (max 3 attempts).

Supported jurisdictions (Phase 1):
  - "us_generic"  → maps to Qdrant collection "legal_corpus_us"
  - "uk"          → maps to Qdrant collection "legal_corpus_uk"
  - "unknown"     → flagged; graph routes to error terminal or falls back to us_generic

Routing:
  After this node, graph/routers.route_after_jurisdiction() reads
  state["jurisdiction_result"]["jurisdiction"] to select the corpus collection.

Extension points (pluggable jurisdiction design):
  - retrieval/corpus_router.py maps jurisdiction string → Qdrant collection name
  - Adding a new jurisdiction requires only: (a) a new collection, (b) an entry in
    corpus_router.JURISDICTION_MAP. No changes needed here.
"""

from __future__ import annotations

from typing import Any, ClassVar

from agents.base_agent import BaseAgent
from graph.state import ThemisState
from schemas.jurisdiction import JurisdictionResult

# TODO (Phase 1): Implement _run():
#   1. Extract first ~2000 chars of state["raw_text"] as classification context
#   2. Build a system prompt explaining the task + supported jurisdictions
#   3. Call Ollama via LangChain ChatOllama with structured output (JurisdictionResult)
#   4. Retry up to 3 times on validation failure
#   5. Return {"jurisdiction_result": result.model_dump()}


class JurisdictionClassifierAgent(BaseAgent):
    node_name: ClassVar[str] = "jurisdiction_classifier"
    output_schema: ClassVar[type[JurisdictionResult]] = JurisdictionResult

    async def _run(self, state: ThemisState) -> dict[str, Any]:
        raise NotImplementedError("Phase 1: JurisdictionClassifierAgent._run() not implemented")
