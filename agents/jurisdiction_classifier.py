"""
agents/jurisdiction_classifier.py — Agent 1: Jurisdiction Classifier.

Responsibility:
  Reads state["raw_text"] (first ~3000 chars of the contract), calls Ollama
  (llama3.1:8b) to classify the governing-law jurisdiction, validates the JSON
  output against JurisdictionClassification, and writes the result to
  state["jurisdiction_result"].

Model strategy:
  - Uses ChatOllama (langchain-ollama) with JSON-mode formatting.
  - Structured output enforced manually: the prompt instructs the LLM to return
    ONLY a JSON object matching JurisdictionClassification. We parse with Pydantic.
  - Retry once on ValidationError with an error-correction prompt that includes
    the original response + validation error message.
  - On permanent failure (both attempts fail), appends to state["errors"] and
    falls back to jurisdiction="us_generic", confidence=0.0, fallback_used=True.

Why not langchain with_structured_output()?
  Ollama's JSON mode is the most reliable structured output path for local models.
  LangChain's with_structured_output() passes through to JSON mode anyway, but
  adds version-coupling risk. We do the JSON parse ourselves to stay explicit.

Supported jurisdictions:
  "us_generic"  → maps to Qdrant collection "themis_us_generic"
  "uk"          → maps to Qdrant collection "themis_uk"
"""

from __future__ import annotations

import datetime
import json
import logging
import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import ValidationError

from graph.state import ThemisState
from schemas.jurisdiction import JurisdictionClassification

logger = logging.getLogger(__name__)

# Only the first CONTEXT_CHARS characters are used for classification.
# Most governing-law clauses appear in the first 2–3 pages.
CONTEXT_CHARS = 3000

_SYSTEM_PROMPT = """\
You are a legal jurisdiction classifier. Your task is to determine the governing law
of a contract based on its text.

Supported jurisdictions:
  - "us_generic" — United States law (any US state, or unspecified US law)
  - "uk"         — English, Welsh, or Scottish law

Rules:
  1. Look for an explicit "Governing Law" or "Choice of Law" clause.
  2. If found, extract its verbatim text and set jurisdiction accordingly.
  3. If no explicit clause, infer from terminology (e.g. "Company Acts", "Corporations Act").
  4. Default to "us_generic" if ambiguous. Set fallback_used=true in that case.
  5. Confidence: 0.9–1.0 if governing-law clause found, 0.5–0.8 for inferred, 0.3–0.5 if fallback.

You MUST respond with ONLY a JSON object — no prose, no markdown, no explanation.
The JSON object must match this exact schema:
{
  "jurisdiction": "us_generic" | "uk",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<one to three sentences explaining the determination>",
  "governing_law_clause_text": "<verbatim clause text or null>",
  "fallback_used": <true|false>
}
"""

_CORRECTION_PROMPT = """\
Your previous response could not be parsed as valid JSON matching the required schema.

Validation error: {error}

Your previous response:
{previous_response}

Respond ONLY with a corrected JSON object — no prose, no markdown fences.
"""


def classify_jurisdiction(state: ThemisState) -> dict[str, Any]:
    """
    LangGraph node: classify jurisdiction from contract raw_text.

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
    llm = _build_llm()

    # ── Attempt 1 ────────────────────────────────────────────────────────────
    user_msg = f"Classify the governing law of this contract:\n\n{context}"
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ]
    callbacks = _get_callbacks(state)
    response_text = _invoke_llm(llm, messages, callbacks, attempt=1)

    result, error = _parse_and_validate(response_text)
    if result is not None:
        logger.info(
            "jurisdiction_classifier: success on attempt 1 — %s (conf=%.2f)",
            result.jurisdiction,
            result.confidence,
        )
        return {"jurisdiction_result": result.model_dump()}

    # ── Attempt 2 (error-correction retry) ───────────────────────────────────
    logger.warning(
        "jurisdiction_classifier: attempt 1 validation failed: %s — retrying", error
    )
    correction = _CORRECTION_PROMPT.format(
        error=error,
        previous_response=response_text,
    )
    messages.append(HumanMessage(content=correction))
    response_text2 = _invoke_llm(llm, messages, callbacks, attempt=2)

    result, error2 = _parse_and_validate(response_text2)
    if result is not None:
        logger.info(
            "jurisdiction_classifier: success on attempt 2 — %s (conf=%.2f)",
            result.jurisdiction,
            result.confidence,
        )
        return {"jurisdiction_result": result.model_dump()}

    # ── Both attempts failed — fallback ──────────────────────────────────────
    logger.error(
        "jurisdiction_classifier: both attempts failed. Error: %s. Using fallback.",
        error2,
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
        message=f"Both LLM attempts failed validation. Last error: {error2}",
    )
    existing_errors: list[dict[str, Any]] = list(state.get("errors") or [])
    return {
        "jurisdiction_result": fallback.model_dump(),
        "errors": existing_errors + [error_record],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_llm() -> ChatOllama:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_CLASSIFY_MODEL", "llama3.1:8b")
    return ChatOllama(
        model=model,
        base_url=host,
        temperature=0,          # deterministic output
        format="json",          # JSON mode: Ollama will always return valid JSON
        timeout=120,
    )


def _invoke_llm(
    llm: ChatOllama,
    messages: list,
    callbacks: list,
    attempt: int,
) -> str:
    """Invoke the LLM and return the raw text response."""
    try:
        response = llm.invoke(messages, config={"callbacks": callbacks})
        return response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        logger.warning("LLM invocation error on attempt %d: %s", attempt, exc)
        return ""


def _parse_and_validate(
    text: str,
) -> tuple[JurisdictionClassification | None, str]:
    """
    Attempt to parse LLM text output as JurisdictionClassification.

    Returns:
        (JurisdictionClassification, "") on success.
        (None, error_message) on failure.
    """
    if not text.strip():
        return None, "LLM returned empty response"

    # Strip markdown code fences if the model included them despite JSON mode
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:-1]) if len(lines) > 2 else clean

    try:
        data = json.loads(clean)
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e} | raw: {clean[:200]}"

    try:
        return JurisdictionClassification.model_validate(data), ""
    except ValidationError as e:
        return None, f"Schema validation: {e}"


def _get_callbacks(state: ThemisState) -> list:
    """Return Langfuse callbacks if configured, else empty list."""
    try:
        from observability.langfuse_callbacks import get_langfuse_handler_for_node
        handler = get_langfuse_handler_for_node(
            state=dict(state),
            node_name="jurisdiction_classifier",
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
