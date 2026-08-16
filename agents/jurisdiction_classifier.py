"""
agents/jurisdiction_classifier.py — Agent 1: Jurisdiction Classifier.

Responsibility:
  Reads state["raw_text"] (first ~3000 chars of the contract), calls the MCP tool
  classify_jurisdiction (which uses Ollama llama3.1:8b) to classify the governing-law
  jurisdiction, validates the JSON output against JurisdictionClassification, and writes
  the result to state["jurisdiction_result"].
"""

from __future__ import annotations

import datetime
import json
import logging
import os
from typing import Any

from pydantic import ValidationError

from graph.state import ThemisState
from schemas.jurisdiction import JurisdictionClassification
from utils.mcp_client import call_mcp_tool

logger = logging.getLogger(__name__)

# Only the first CONTEXT_CHARS characters are used for classification.
# Most governing-law clauses appear in the first 2–3 pages.
CONTEXT_CHARS = 3000

def classify_jurisdiction(state: ThemisState) -> dict[str, Any]:
    """
    LangGraph node: classify jurisdiction from contract raw_text via MCP.

    Args:
        state: Current ThemisState. Must contain 'raw_text'.

    Returns:
        Partial ThemisState update dict with 'jurisdiction_result' and optionally 'errors'.
    """
    raw_text: str = state.get("raw_text", "")
    if not raw_text:
        logger.error("jurisdiction_classifier: raw_text is empty")
        return _error_result(
            state,
            "raw_text is empty — cannot classify jurisdiction",
            "ValueError",
        )

    context = raw_text[:CONTEXT_CHARS]
    
    # Call MCP Server
    mcp_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools", "mcp", "jurisdiction_router_server.py"))
    
    try:
        response_text = call_mcp_tool(mcp_script, "classify_jurisdiction", {"text": context})
    except Exception as e:
        logger.error(f"jurisdiction_classifier: MCP call failed: {e}")
        return _error_result(state, f"MCP tool failure: {e}", "MCPError")
        
    result, error = _parse_and_validate(response_text)
    if result is not None:
        logger.info(
            "jurisdiction_classifier: success — %s (conf=%.2f)",
            result.jurisdiction,
            result.confidence,
        )
        return {"jurisdiction_result": result.model_dump()}

    # ── Failed — fallback ──────────────────────────────────────
    logger.error(
        "jurisdiction_classifier: LLM attempts failed. Error: %s. Using fallback.",
        error,
    )
    fallback = JurisdictionClassification(
        jurisdiction="us_generic",
        confidence=0.0,
        reasoning="Jurisdiction could not be determined; defaulted to us_generic.",
        fallback_used=True,
    )
    error_record = _make_error_record(
        node="jurisdiction_classifier",
        error_type="ValidationError",
        message=f"LLM attempts failed validation. Error: {error}",
    )
    existing_errors: list[dict[str, Any]] = list(state.get("errors") or [])
    return {
        "jurisdiction_result": fallback.model_dump(),
        "errors": existing_errors + [error_record],
    }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_and_validate(
    text: str,
) -> tuple[JurisdictionClassification | None, str]:
    """
    Attempt to parse MCP text output as JurisdictionClassification.
    """
    if not text or not text.strip():
        return None, "MCP returned empty response"

    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:-1]) if len(lines) > 2 else clean

    try:
        data = json.loads(clean)
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e} | raw: {clean[:200]}"
        
    if "error" in data:
        return None, f"MCP internal error: {data['error']}"

    try:
        return JurisdictionClassification.model_validate(data), ""
    except ValidationError as e:
        return None, f"Schema validation: {e}"

def _make_error_record(node: str, error_type: str, message: str) -> dict[str, Any]:
    return {
        "node": node,
        "error_type": error_type,
        "message": message,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }

def _error_result(
    state: ThemisState, message: str, error_type: str
) -> dict[str, Any]:
    fallback = JurisdictionClassification(
        jurisdiction="us_generic",
        confidence=0.0,
        reasoning=message,
        fallback_used=True,
    )
    existing_errors: list[dict[str, Any]] = list(state.get("errors") or [])
    return {
        "jurisdiction_result": fallback.model_dump(),
        "errors": existing_errors + [_make_error_record("jurisdiction_classifier", error_type, message)],
    }
