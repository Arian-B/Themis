"""
agents/extraction_agent.py — Agent 2: Contract Extraction Agent.

Responsibility:
  Reads state["raw_text"], segments the contract into meaningful clauses using
  a section-heading heuristic, classifies each clause via Ollama (llama3.1:8b),
  validates the full result against ExtractionResult, and writes to
  state["extraction_result"].

Clause segmentation strategy:
  1. Split on numbered section headings (e.g. "1.", "2.1", "SECTION 3.").
  2. Each segment is sent to Ollama with the full list of supported clause types.
  3. Ollama returns JSON: {clause_type, section_reference}.
  4. We build ExtractedClause objects combining the LLM output with the segment text.

Retry pattern:
  - If ExtractionResult.model_validate() fails, retry once with error-correction prompt.
  - On permanent failure, append to state["errors"] and return whatever clauses were
    successfully parsed (partial results are better than nothing for downstream agents).

Model:
  ChatOllama with format="json" and temperature=0.
  Same model as jurisdiction_classifier (llama3.1:8b) — one model, two uses.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from utils.llm_provider import get_complex_reasoning_llm
from pydantic import ValidationError

from graph.state import ThemisState
from schemas.contract import ExtractedClause, ExtractionResult

logger = logging.getLogger(__name__)

# ── Prompt constants ──────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a legal contract analyst. You will receive the text of one section or clause
from a contract. Your task is to:
  1. Classify the clause type using ONLY these values:
       termination | payment_terms | liability | auto_renewal | non_compete |
       indemnification | confidentiality | ip_ownership | data_protection |
       representations_warranties | account_admin | other

     Definitions to prevent misclassification:
       - liability: ONLY limitation of liability or exclusion of damages. Do NOT use for general obligations.
       - non_compete: ONLY for clauses restricting a party from competing in a market. Do NOT use for software license usage restrictions (use 'other' or 'ip_ownership' for software license restrictions).
       - ip_ownership: Clauses defining who owns intellectual property, software, or data.
       - data_protection: Clauses regarding data privacy, GDPR, CCPA, or data security.
       - representations_warranties: Mutual representations, warranties, or disclaimers of warranty.
       - account_admin: Rules about user accounts, passwords, or administrative access.
       - other: Use this if it doesn't clearly fit the above (e.g., general software license grants or restrictions).

  2. Identify the section reference (number or heading).

Respond ONLY with a JSON object. No prose, no markdown fences.
Schema:
{
  "clause_type": "<one of the values above>",
  "section_reference": "<section number or heading, e.g. '3.1 Fees' or 'Section 9'>"
}
"""

_CORRECTION_PROMPT = """\
Your previous response could not be parsed as valid JSON.
Validation error: {error}
Your previous response: {previous_response}
Respond ONLY with a corrected JSON object.
"""

# Minimum characters for a segment to be treated as a clause (filters out headings-only)
_MIN_CLAUSE_CHARS = 60

# Maximum clauses to extract (prevents runaway on very long contracts)
_MAX_CLAUSES = 30


def extract_clauses(state: ThemisState) -> dict[str, Any]:
    """
    LangGraph node: extract and classify clauses from contract raw_text.

    Args:
        state: Current ThemisState. Must contain 'raw_text' and 'contract_id'.

    Returns:
        Partial ThemisState update dict with 'extraction_result' and optionally 'errors'.
    """
    raw_text: str = state.get("raw_text", "")
    contract_id: str = state.get("contract_id", str(uuid.uuid4()))

    if not raw_text:
        logger.error("extraction_agent: raw_text is empty")
        return _error_result(
            state,
            contract_id,
            "raw_text is empty — cannot extract clauses",
            "ValueError",
        )

    # ── Step 1: Segment the contract ─────────────────────────────────────────
    segments = _segment_contract(raw_text)
    logger.info("extraction_agent: segmented into %d candidate clauses", len(segments))

    if not segments:
        return _error_result(
            state,
            contract_id,
            "No clause segments found in contract text",
            "ExtractionError",
        )

    # ── Step 2: Classify each segment via Ollama ─────────────────────────────
    llm = _build_llm()
    callbacks = _get_callbacks(state)
    clauses: list[ExtractedClause] = []
    errors: list[dict[str, Any]] = list(state.get("errors") or [])

    for i, (heading, text) in enumerate(segments[:_MAX_CLAUSES]):
        clause = _classify_segment(
            llm=llm,
            heading=heading,
            text=text,
            callbacks=callbacks,
            index=i,
        )
        if clause is not None:
            clauses.append(clause)
        else:
            logger.warning("extraction_agent: segment %d could not be classified — skipped", i)

    logger.info("extraction_agent: extracted %d clauses", len(clauses))

    # ── Step 3: Build and validate ExtractionResult ───────────────────────────
    try:
        result = ExtractionResult(contract_id=contract_id, clauses=clauses)
    except ValidationError as e:
        logger.error("extraction_agent: ExtractionResult validation failed: %s", e)
        errors.append(
            _make_error_record(
                "extraction_agent",
                "ValidationError",
                f"ExtractionResult build failed: {e}",
            )
        )
        # Return partial result to avoid blocking downstream completely
        result = ExtractionResult(contract_id=contract_id, clauses=clauses)

    return {
        "extraction_result": result.model_dump(),
        **({"errors": errors} if errors else {}),
    }


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

def _segment_contract(text: str) -> list[tuple[str, str]]:
    """
    Split contract text into (heading, body) pairs using numbered section detection.

    Matches patterns like:
      "1. FEES AND PAYMENT"
      "3.1 Subscription"
      "SECTION 7. TERMINATION"
      "ARTICLE II — CONFIDENTIALITY"
    """
    # Pattern: line starting with number(s) or SECTION/ARTICLE keyword
    pattern = re.compile(
        r"(?m)^(?=(?:\d+(?:\.\d+)*\.?\s+[A-Z])|(?:SECTION|ARTICLE)\s+\d*)",
        re.IGNORECASE,
    )
    parts = pattern.split(text)
    # Re-attach the matched heading by splitting differently
    raw_segments = re.split(
        r"(?m)(?=^\d+(?:\.\d+)*\.?\s+[A-Z])|(?=^(?:SECTION|ARTICLE)\s+\d*)",
        text,
        flags=re.IGNORECASE,
    )

    segments: list[tuple[str, str]] = []
    for seg in raw_segments:
        seg = seg.strip()
        if len(seg) < _MIN_CLAUSE_CHARS:
            continue
        # First line is the heading
        lines = seg.split("\n", 1)
        heading = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else seg
        if len(body) >= _MIN_CLAUSE_CHARS:
            segments.append((heading, seg))  # full segment (heading+body) as clause text

    # Fallback: if no sections found, split on double newlines
    if not segments:
        paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if len(p.strip()) >= _MIN_CLAUSE_CHARS]
        segments = [(f"Paragraph {i+1}", p) for i, p in enumerate(paragraphs)]

    return segments


# ---------------------------------------------------------------------------
# Per-segment classification
# ---------------------------------------------------------------------------

def _classify_segment(
    llm,
    heading: str,
    text: str,
    callbacks: list,
    index: int,
) -> ExtractedClause | None:
    """Classify a single contract segment. Returns None on permanent failure."""
    prompt_text = f"Heading: {heading}\n\nFull clause text:\n{text[:1500]}"
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=prompt_text),
    ]

    # Attempt 1
    raw = _invoke_llm(llm, messages, callbacks, attempt=1)
    clause_data, error = _parse_clause_json(raw)

    if clause_data is None:
        # Attempt 2: error-correction
        logger.debug("extraction_agent: segment %d attempt 1 failed (%s) — retrying", index, error)
        correction = _CORRECTION_PROMPT.format(error=error, previous_response=raw)
        messages.append(HumanMessage(content=correction))
        raw2 = _invoke_llm(llm, messages, callbacks, attempt=2)
        clause_data, error2 = _parse_clause_json(raw2)
        if clause_data is None:
            logger.warning(
                "extraction_agent: segment %d failed both attempts. Error: %s", index, error2
            )
            return None

    try:
        return ExtractedClause(
            clause_id=str(uuid.uuid4()),
            clause_type=clause_data["clause_type"],
            text=text,
            section_reference=clause_data.get("section_reference", heading or f"Section {index+1}"),
        )
    except (ValidationError, KeyError) as e:
        logger.warning("extraction_agent: ExtractedClause build failed for segment %d: %s", index, e)
        return None


def _parse_clause_json(text: str) -> tuple[dict | None, str]:
    """Parse and validate a clause classification JSON response."""
    if not text.strip():
        return None, "empty response"

    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:-1]) if len(lines) > 2 else clean

    try:
        data = json.loads(clean)
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"

    valid_types = {
        "termination", "payment_terms", "liability", "auto_renewal",
        "non_compete", "indemnification", "confidentiality",
        "ip_ownership", "data_protection", "representations_warranties",
        "account_admin", "other",
    }
    clause_type = data.get("clause_type", "").strip().lower()
    if clause_type not in valid_types:
        # Attempt fuzzy map before failing
        clause_type = _fuzzy_map_clause_type(clause_type, valid_types)
        if clause_type is None:
            return None, f"clause_type '{data.get('clause_type')}' not in allowed set"
        data["clause_type"] = clause_type

    return data, ""


def _fuzzy_map_clause_type(raw: str, valid: set[str]) -> str | None:
    """Map common LLM mis-classifications to the canonical enum values."""
    mappings: dict[str, str] = {
        "limitation_of_liability": "liability",
        "limitation of liability": "liability",
        "intellectual_property": "ip_ownership",
        "intellectual property": "ip_ownership",
        "force_majeure": "other",
        "force majeure": "other",
        "dispute_resolution": "other",
        "dispute resolution": "other",
        "representations and warranties": "representations_warranties",
        "governing_law": "other",
        "governing law": "other",
        "non-compete": "non_compete",
        "non compete": "non_compete",
        "auto renewal": "auto_renewal",
        "subscription": "payment_terms",
        "fees": "payment_terms",
        "payment": "payment_terms",
        "termination and effect": "termination",
    }
    return mappings.get(raw.lower())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_llm():
    import os
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model="llama3.1:8b",
        base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        temperature=0,
        format="json",
    )


def _invoke_llm(
    llm,
    messages: list,
    callbacks: list,
    attempt: int,
) -> str:
    try:
        response = llm.invoke(messages, config={"callbacks": callbacks})
        return response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        logger.warning("LLM invocation error on attempt %d: %s", attempt, exc)
        return ""


def _get_callbacks(state: ThemisState) -> list:
    try:
        from observability.langfuse_callbacks import get_langfuse_handler_for_node
        handler = get_langfuse_handler_for_node(
            state=dict(state),
            node_name="extraction_agent",
        )
        return [handler] if handler is not None else []
    except Exception:
        return []


def _make_error_record(node: str, error_type: str, message: str) -> dict[str, Any]:
    return {
        "node": node,
        "error_type": error_type,
        "message": message,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }


def _error_result(
    state: ThemisState,
    contract_id: str,
    message: str,
    error_type: str,
) -> dict[str, Any]:
    existing_errors: list[dict[str, Any]] = list(state.get("errors") or [])
    return {
        "extraction_result": ExtractionResult(
            contract_id=contract_id, clauses=[]
        ).model_dump(),
        "errors": existing_errors + [
            _make_error_record("extraction_agent", error_type, message)
        ],
    }
