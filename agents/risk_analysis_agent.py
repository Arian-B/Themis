"""
agents/risk_analysis_agent.py — Agent 3: Risk Analysis Agent.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from graph.state import ThemisState
from schemas.risk import RiskFlag
from tools.pii.redactor import redact_pii
from utils.mcp_client import call_mcp_tool

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an expert commercial lawyer and risk analyst.
You will be provided with:
1. A specific contract clause to analyze.
2. Historical precedent chunks retrieved from a vector database (grounding context).

Your task is to identify IF there is a legal or commercial risk in the provided clause,
based primarily on how it compares to the historical precedent.

Respond ONLY with a JSON object. No prose.
If there is NO significant risk, return an empty JSON object: {}
If there is a risk, return exactly this JSON schema:
{
  "risk_level": "low" | "medium" | "high",
  "concern": "<Plain language explanation of the risk, omitting legal jargon>",
  "reasoning": "<Step-by-step legal reasoning explaining why it is a risk>",
  "retrieved_source_ids": ["<Qdrant ID of the historical chunk that supports this finding, if any>"]
}
"""

_CORRECTION_PROMPT = """\
Your previous response could not be parsed as valid JSON.
Validation error: {error}
Your previous response: {previous_response}
Respond ONLY with a corrected JSON object.
"""

def analyze_risk(state: ThemisState) -> dict[str, Any]:
    """
    LangGraph node: analyzes extracted clauses for risk using Kimi.
    """
    ext_result = state.get("extraction_result")
    if not ext_result or not ext_result.get("clauses"):
        logger.warning("risk_analysis_agent: No extraction result found in state.")
        return {}

    jurisdiction = state.get("jurisdiction_result", {}).get("jurisdiction", "us_generic")
    
    mcp_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools", "mcp", "retrieval_server.py"))

    llm = _build_llm()
    errors: list[dict[str, Any]] = list(state.get("errors") or [])
    risk_flags: list[dict[str, Any]] = []

    for clause in ext_result["clauses"]:
        clause_id = clause.get("clause_id")
        raw_text = clause.get("text", "")
        if not raw_text:
            continue

        # Redact PII before sending to the external LLM
        redacted_text = redact_pii(raw_text)

        # Retrieve grounding context via MCP
        try:
            docs_json = call_mcp_tool(mcp_script, "search_corpus", {"query": redacted_text, "jurisdiction": jurisdiction, "k": 3})
            docs = json.loads(docs_json)
            if isinstance(docs, dict) and "error" in docs:
                logger.error(f"risk_analysis_agent: MCP retrieval error: {docs['error']}")
                docs = []
        except Exception as e:
            logger.error(f"risk_analysis_agent: failed to call MCP retrieval: {e}")
            docs = []

        context_parts = []
        for i, doc in enumerate(docs):
            # doc is a dict from MCP: {"id": ..., "content": ..., "metadata": ...}
            doc_id = doc.get("id") or f"doc_{i}"
            content = doc.get("content", "")
            context_parts.append(f"--- Document ID: {doc_id} ---\n{content}")
        
        context_str = "\n\n".join(context_parts)
        
        prompt_text = (
            f"CLAUSE TO ANALYZE:\n{redacted_text}\n\n"
            f"HISTORICAL PRECEDENT (GROUNDING CONTEXT):\n{context_str}"
        )
        
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=prompt_text),
        ]

        raw = _invoke_llm(llm, messages, attempt=1)
        data, err = _parse_json(raw)

        if err:
            logger.debug(f"risk_analysis_agent: attempt 1 failed ({err}) - retrying")
            correction = _CORRECTION_PROMPT.format(error=err, previous_response=raw)
            messages.append(HumanMessage(content=correction))
            raw2 = _invoke_llm(llm, messages, attempt=2)
            data, err2 = _parse_json(raw2)
            if err2:
                logger.warning(f"risk_analysis_agent: failed both attempts for clause {clause_id}.")
                errors.append({
                    "node": "risk_analysis_agent",
                    "error_type": "JSONParseError",
                    "message": f"Failed to parse risk for clause {clause_id}: {err2}",
                    "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
                })
                continue
        
        if not data:
            continue # empty dict = no risk

        # Add clause_id and validate against schema
        data["clause_id"] = clause_id
        try:
            flag = RiskFlag(**data)
            risk_flags.append(flag.model_dump())
        except ValidationError as e:
            logger.error(f"risk_analysis_agent: Schema validation failed: {e}")
            errors.append({
                "node": "risk_analysis_agent",
                "error_type": "ValidationError",
                "message": f"RiskFlag schema invalid: {e}",
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
            })

    logger.info(f"risk_analysis_agent: identified {len(risk_flags)} unverified risk flags.")
    return {
        "risk_analysis_result": risk_flags,
        **({"errors": errors} if errors else {}),
    }

from utils.llm_provider import get_complex_reasoning_llm

def _build_llm() -> ChatOpenAI:
    return get_complex_reasoning_llm(temperature=0)

def _invoke_llm(llm: ChatOpenAI, messages: list, attempt: int) -> str:
    try:
        response = llm.invoke(messages)
        return response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        logger.warning("LLM invocation error on attempt %d: %s", attempt, exc)
        return ""

def _parse_json(text: str) -> tuple[dict | None, str]:
    if not text.strip():
        return None, "empty response"
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:-1]) if len(lines) > 2 else clean
    try:
        return json.loads(clean), ""
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"
