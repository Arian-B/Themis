"""
agents/extraction_agent.py — Agent 2: Contract Extraction Agent.

Responsibility:
  Receives state["raw_pdf_bytes"], converts the PDF to text (via pdfplumber or
  pymupdf), segments the text into individual clauses, classifies each clause
  by type, and writes a structured ClauseBundle to state["clause_bundle"].

  After writing clause_bundle, this agent clears state["raw_pdf_bytes"] to
  prevent large binary payloads from persisting in LangGraph checkpoints.

Model strategy:
  - PDF-to-text: pdfplumber (no LLM needed for text extraction).
  - Clause segmentation: rule-based regex + heading detection first; LLM
    fallback (Ollama) only for ambiguous boundaries.
  - Clause classification: Ollama with structured output (ClauseType enum).

Clause types supported (extensible via ClauseType enum in schemas/contract.py):
  INDEMNIFICATION | LIMITATION_OF_LIABILITY | PAYMENT_TERMS |
  TERMINATION | GOVERNING_LAW | CONFIDENTIALITY | INTELLECTUAL_PROPERTY |
  FORCE_MAJEURE | DISPUTE_RESOLUTION | REPRESENTATIONS_WARRANTIES | OTHER

PII pre-processing:
  Raw text is passed through Presidio redaction (api/middleware/pii_redaction.py)
  BEFORE being stored in state or sent to any LLM. The redacted text is what
  gets embedded into Qdrant and stored in Neo4j.

Output: state["clause_bundle"] = ClauseBundle.model_dump()
"""

from __future__ import annotations

from typing import Any, ClassVar

from agents.base_agent import BaseAgent
from graph.state import ThemisState
from schemas.contract import ClauseBundle

# TODO (Phase 1): Implement _run():
#   1. Extract raw_pdf_bytes from state; convert to text via pdfplumber
#   2. Pass text through Presidio redaction middleware
#   3. Segment text into clause candidates via regex + heading detection
#   4. For each candidate: call Ollama to classify clause type
#   5. Build ClauseBundle, validate with PydanticAI, return {"clause_bundle": ...}
#   6. Clear state["raw_pdf_bytes"] (set to b"") after successful extraction


class ExtractionAgent(BaseAgent):
    node_name: ClassVar[str] = "extraction_agent"
    output_schema: ClassVar[type[ClauseBundle]] = ClauseBundle

    async def _run(self, state: ThemisState) -> dict[str, Any]:
        raise NotImplementedError("Phase 1: ExtractionAgent._run() not implemented")
