"""
agents/verification_agent.py — Agent 4: Atomic Verification Agent.

Responsibility:
  For each RiskFlag produced by risk_analysis_agent:
    1. Decompose the flag's concern + reasoning into OBJECTIVE, checkable
       factual claims about what the contract actually states.
    2. For each claim, FIRST attempt to ground it against the clause's own
       extracted text (contract_text path — no embedding needed, instant).
    3. Only if the claim makes a broader legal/normative assertion that the
       clause text cannot confirm, fall through to the Qdrant statute corpus
       (statute_corpus path — cosine similarity with threshold gate).
    4. Record grounded=True only if the source directly and unambiguously
       supports the claim. Record which source was used (grounding_source).

Grounding philosophy:
  Themis never surfaces a legal risk assertion without a grounded source.
  A claim is UNVERIFIED unless the text directly and unambiguously
  supports it — speculation, inference, and interpretive commentary are
  never grounded.

Grounding sources (in order of priority):
  1. contract_text — the clause's own extracted text (already in state).
     Used for claims about specific contract provisions (notice periods,
     named parties, fees, dates, explicit inclusions/exclusions).
  2. statute_corpus — Qdrant collection 'themis_{jurisdiction}'.
     Used for claims asserting legal/regulatory significance
     ("this is prohibited by UCC § X", "this lacks standard protections").
     ONLY queried if top Qdrant cosine score >= VERIFICATION_COSINE_THRESHOLD.
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
from pydantic import BaseModel, ValidationError

from graph.state import ThemisState
from schemas.risk import AtomicClaim, VerificationResult
from utils.mcp_client import call_mcp_tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Minimum Qdrant cosine score required before sending a retrieved chunk to
# the LLM for verification. Claims whose top match is below this threshold
# are immediately marked UNVERIFIED without an LLM call.
_DEFAULT_COSINE_THRESHOLD = float(os.getenv("VERIFICATION_COSINE_THRESHOLD", "0.65"))

# Minimum fraction of the claim text that must appear (case-insensitive) in
# the clause text for a contract_text grounding to succeed.
# Using LLM for this check since substring match is too brittle for paraphrases.
_CONTRACT_TEXT_MIN_SIMILARITY = 0.0  # LLM-based; no numeric threshold needed


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_DECOMPOSITION_PROMPT = """\
You are a legal verification engine preparing factual claims for grounding checks.

Your task: given a Risk Concern and its Reasoning, extract ONLY the objective,
directly checkable factual assertions about what the contract clause ITSELF STATES.

STRICT RULES:
  - Include ONLY claims that can be confirmed by reading the clause text directly.
  - A good claim quotes or closely paraphrases a specific provision in the clause.
  - Do NOT include claims that reference other documents, "doc_0", "historical precedents",
    or any external comparison — only what THIS clause says.
  - Do NOT include claims about what "could" happen, what "may" be the case, or
    what you interpret the risk to be — those are analysis, not verifiable facts.
  - Do NOT include comparative statements about what other contracts do differently.
  - Do NOT include meta-commentary about the decomposition process itself.
  - Write each claim as if explaining to someone who has never read the contract —
    use plain language, reference the clause content directly.

EXAMPLES:
  GOOD (verifiable from clause text):
    - "The notice period for non-renewal is 60 days."
    - "Liability is capped at the total fees paid in the preceding 12 months."
    - "The contract excludes liability for consequential damages."
    - "The contract renews automatically for successive terms of the same duration."
    - "The Customer is solely responsible for the accuracy and legality of Customer Data."

  BAD (exclude these — they reference other docs or are non-verifiable):
    - "The clause mirrors the language from doc_0."
    - "Historical precedents often emphasize the importance of consequential damages."
    - "One party may be more likely to cause consequential damages than the other."
    - "This could disproportionately favor one party."
    - "Unlike the standard market template, this clause lacks X."

Respond ONLY with a JSON array of strings (the verifiable claims).
Produce no more than 5 claims per flag. Aim for 2-4.

Example output format:
[
  "The contract excludes liability for consequential damages.",
  "Liability is capped at fees paid in the preceding 12 months."
]
"""

_CONTRACT_TEXT_VERIFY_PROMPT = """\
You are an objective auditor verifying a factual claim against a specific contract clause.

Rule 1: The claim must be directly supported by the CONTRACT CLAUSE TEXT provided.
Rule 2: Paraphrase matches are acceptable — exact wording is not required.
Rule 3: If the clause text is silent on the claim, or contradicts it, output grounded=false.
Rule 4: Do not use outside knowledge. Only use the CONTRACT CLAUSE TEXT provided.

Respond ONLY with a JSON object:
{
  "grounded": true | false,
  "confidence": <float 0.0-1.0>
}
"""

_STATUTE_VERIFY_PROMPT = """\
You are an objective auditor.
Determine if the provided CLAIM is directly supported by the SOURCE TEXT.

Rule 1: The claim must be unequivocally supported by the source text.
Rule 2: If the source text is irrelevant, contradictory, or lacks enough detail to prove
        the claim, it is NOT grounded.
Rule 3: Do not use outside knowledge. Only use what is in the SOURCE TEXT.
Rule 4: Paraphrase matches are acceptable — the claim need not be a verbatim quote.

Respond ONLY with a JSON object:
{
  "grounded": true | false,
  "confidence": <float 0.0-1.0>
}
"""

_CORRECTION_PROMPT = """\
Your previous response could not be parsed as valid JSON.
Validation error: {error}
Your previous response: {previous_response}
Respond ONLY with a corrected JSON object/array.
"""


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------

def verify_risks(state: ThemisState) -> dict[str, Any]:
    """
    LangGraph node: decomposes risk flags into atomic claims and verifies them
    against (1) the clause's own text first, (2) the Qdrant statute corpus only
    for legal/normative assertions that the clause text can't confirm.
    """
    risk_flags = state.get("risk_analysis_result")
    if not risk_flags:
        logger.warning("verification_agent: No risk flags found in state.")
        return {}

    jurisdiction = state.get("jurisdiction_result", {}).get("jurisdiction", "us_generic")
    collection_name = f"themis_{jurisdiction}"
    cosine_threshold = _DEFAULT_COSINE_THRESHOLD

    logger.info(
        "[CORPUS] Statute corpus: '%s' | cosine_threshold=%.2f | "
        "Contract-text grounding takes priority for factual claims.",
        collection_name, cosine_threshold,
    )

    # Build the clause lookup map: clause_id → clause text + section reference
    extraction_result = state.get("extraction_result") or {}
    clauses_list = extraction_result.get("clauses", [])
    clause_map: dict[str, dict] = {c["clause_id"]: c for c in clauses_list}
    
    contract_id = state.get("contract_id", "")

    mcp_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools", "mcp", "retrieval_server.py"))

    llm = _build_llm()
    errors: list[dict[str, Any]] = list(state.get("errors") or [])
    verification_results: list[dict[str, Any]] = []

    for flag_dict in risk_flags:
        flag_id = flag_dict.get("clause_id") + "_risk"
        clause_id = flag_dict.get("clause_id", "")
        concern = flag_dict.get("concern", "")
        reasoning = flag_dict.get("reasoning", "")

        # Retrieve the source clause text (already extracted — no embedding needed)
        clause_data = clause_map.get(clause_id, {})
        clause_text = clause_data.get("text", "") or clause_data.get("clause_text", "")
        section_ref = clause_data.get("section_reference", clause_id)

        logger.info("verification_agent: processing flag '%s' (clause: %s)", flag_id, section_ref)

        # ── Step 1: Decompose into objective atomic claims ──────────────────
        messages = [
            SystemMessage(content=_DECOMPOSITION_PROMPT),
            HumanMessage(content=f"CONCERN: {concern}\nREASONING: {reasoning}"),
        ]

        raw_decomp = _invoke_llm(llm, messages, attempt=1)
        claims_list, err = _parse_json(raw_decomp)

        if err or not isinstance(claims_list, list):
            logger.debug("verification_agent: decomp attempt 1 failed - retrying")
            correction = _CORRECTION_PROMPT.format(
                error=err or "Expected a JSON array",
                previous_response=raw_decomp,
            )
            messages.append(HumanMessage(content=correction))
            raw_decomp2 = _invoke_llm(llm, messages, attempt=2)
            claims_list, err2 = _parse_json(raw_decomp2)
            if err2 or not isinstance(claims_list, list):
                logger.warning("verification_agent: failed decomp for flag %s.", flag_id)
                continue

        logger.info(
            "verification_agent: flag '%s' decomposed into %d claims: %s",
            flag_id, len(claims_list), claims_list,
        )

        # ── Step 2: Verify each claim ───────────────────────────────────────
        all_grounded = True

        for claim_text_raw in claims_list:
            claim_id = str(uuid.uuid4())
            claim_str = str(claim_text_raw)
            result = _verify_claim(
                claim_str=claim_str,
                claim_id=claim_id,
                flag_id=flag_id,
                clause_text=clause_text,
                clause_id=clause_id,
                contract_id=contract_id,
                jurisdiction=jurisdiction,
                collection_name=collection_name,
                cosine_threshold=cosine_threshold,
                mcp_script=mcp_script,
                llm=llm,
            )

            if not result.grounded:
                all_grounded = False

            verification_results.append(result.model_dump())

        flag_dict["grounded"] = all_grounded

    logger.info(
        "verification_agent: completed %d atomic verifications.", len(verification_results)
    )
    return {
        "verification_result": verification_results,
        **({} if not errors else {"errors": errors}),
    }


# ---------------------------------------------------------------------------
# Claim verification — two-path logic
# ---------------------------------------------------------------------------

def _verify_claim(
    *,
    claim_str: str,
    claim_id: str,
    flag_id: str,
    clause_text: str,
    clause_id: str,
    contract_id: str,
    jurisdiction: str,
    collection_name: str,
    cosine_threshold: float,
    mcp_script: str,
    llm: ChatOpenAI,
) -> VerificationResult:
    """
    Multi-path verification:
      Path A — contract_text: check claim against clause's own extracted text.
      Path B — full_contract_text: check claim against all clauses (via MCP) if A fails.
      Path C — statute_corpus: fall through to Qdrant if A and B don't ground it.
    """

    # ── Path A: contract_text ───────────────────────────────────────────────
    if clause_text.strip():
        ver_msgs = [
            SystemMessage(content=_CONTRACT_TEXT_VERIFY_PROMPT),
            HumanMessage(
                content=f"CONTRACT CLAUSE TEXT:\n{clause_text}\n\nCLAIM: {claim_str}"
            ),
        ]
        raw = _invoke_llm(llm, ver_msgs, attempt=1)
        data, err = _parse_json(raw)

        if data and isinstance(data, dict) and data.get("grounded") is True:
            conf = float(data.get("confidence", 1.0))
            logger.info(
                "  [CONTRACT_TEXT] GROUNDED | claim='%s' | clause=%s | llm_conf=%.2f",
                claim_str, clause_id, conf,
            )
            return VerificationResult(
                claim_id=claim_id,
                source_risk_flag_id=flag_id,
                claim_text=claim_str,
                grounded=True,
                supporting_source_id=clause_id,
                grounding_source="contract_text",
                raw_cosine_score=None,
                confidence=conf,
            )
        else:
            logger.info(
                "  [CONTRACT_TEXT] NOT grounded | claim='%s' → falling through to statute_corpus",
                claim_str,
            )
    else:
        logger.warning(
            "  [CONTRACT_TEXT] No clause text available for clause_id=%s — skipping contract_text path",
            clause_id,
        )

    # ── Path B: full_contract_text (Cross-clause lookup) ─────────────────────
    if contract_id:
        try:
            full_clauses_json = call_mcp_tool(mcp_script, "get_contract_clauses", {"contract_id": contract_id})
            data = json.loads(full_clauses_json)
            full_text = ""
            if "clauses" in data and isinstance(data["clauses"], list):
                # reconstruct full text
                full_text = "\n\n".join([f"{c.get('section_reference', '')}:\n{c.get('text', '')}" for c in data["clauses"]])
                
            if full_text.strip():
                ver_msgs = [
                    SystemMessage(content=_CONTRACT_TEXT_VERIFY_PROMPT),
                    HumanMessage(
                        content=f"FULL CONTRACT TEXT:\n{full_text}\n\nCLAIM: {claim_str}"
                    ),
                ]
                raw = _invoke_llm(llm, ver_msgs, attempt=1)
                ver_data, err = _parse_json(raw)

                if ver_data and isinstance(ver_data, dict) and ver_data.get("grounded") is True:
                    conf = float(ver_data.get("confidence", 1.0))
                    logger.info(
                        "  [FULL_CONTRACT_TEXT] GROUNDED | claim='%s' | contract=%s | llm_conf=%.2f",
                        claim_str, contract_id, conf,
                    )
                    return VerificationResult(
                        claim_id=claim_id,
                        source_risk_flag_id=flag_id,
                        claim_text=claim_str,
                        grounded=True,
                        supporting_source_id=contract_id,
                        grounding_source="contract_text", # Semantically still contract_text
                        raw_cosine_score=None,
                        confidence=conf,
                    )
                else:
                    logger.info(
                        "  [FULL_CONTRACT_TEXT] NOT grounded | claim='%s' → falling through to statute_corpus",
                        claim_str,
                    )
        except Exception as e:
            logger.warning(f"  [FULL_CONTRACT_TEXT] lookup failed: {e}")

    # ── Path C: statute_corpus ──────────────────────────────────────────────
    logger.info("  [PATH C REACHED] Attempting statute_corpus retrieval for claim: '%s'", claim_str)
    # Retrieve with raw cosine scores via MCP
    try:
        docs_json = call_mcp_tool(mcp_script, "search_corpus", {"query": claim_str, "jurisdiction": jurisdiction, "k": 3})
        docs = json.loads(docs_json)
        if isinstance(docs, dict) and "error" in docs:
            logger.error("  [STATUTE_CORPUS] retrieval error: %s", docs["error"])
            docs = []
    except Exception as exc:
        logger.error("  [STATUTE_CORPUS] retrieval failed: %s", exc)
        return _unverified(claim_id, flag_id, claim_str)

    if not docs:
        logger.info("  [STATUTE_CORPUS] 0 docs returned | claim='%s' → UNVERIFIED", claim_str)
        return _unverified(claim_id, flag_id, claim_str)

    # Log all retrieved docs with raw cosine scores
    for di, doc in enumerate(docs):
        doc_id = doc.get("id", "unknown")
        content = doc.get("content", "")
        score = doc.get("score", 0.0)
        preview = content[:150].replace("\n", " ")
        logger.info(
            "  [STATUTE_CORPUS] doc[%d] id=%s raw_cosine=%.6f text='%s...'",
            di, doc_id, score, preview,
        )

    best_doc = docs[0]
    best_score = best_doc.get("score", 0.0)
    best_doc_id = best_doc.get("id", "unknown")

    # ── Cosine threshold gate ───────────────────────────────────────────────
    if best_score < cosine_threshold:
        logger.info(
            "  [THRESHOLD_GATE] BLOCKED | best_cosine=%.6f < threshold=%.2f | "
            "claim='%s' → UNVERIFIED (no LLM call)",
            best_score, cosine_threshold, claim_str,
        )
        return VerificationResult(
            claim_id=claim_id,
            source_risk_flag_id=flag_id,
            claim_text=claim_str,
            grounded=False,
            supporting_source_id=None,
            grounding_source="none",
            raw_cosine_score=best_score,
            confidence=0.0,
        )

    # ── LLM verification against statute corpus ─────────────────────────────
    for doc in docs:
        doc_id = doc.get("id", "unknown")
        score = doc.get("score", 0.0)
        content = doc.get("content", "")

        if score < cosine_threshold:
            logger.info(
                "    [STATUTE_CORPUS] SKIP doc=%s (score=%.6f < threshold)", doc_id, score
            )
            continue

        ver_msgs = [
            SystemMessage(content=_STATUTE_VERIFY_PROMPT),
            HumanMessage(
                content=f"CLAIM: {claim_str}\n\nSOURCE TEXT:\n{content}"
            ),
        ]
        raw_ver = _invoke_llm(llm, ver_msgs, attempt=1)
        ver_data, ver_err = _parse_json(raw_ver)

        if ver_data and isinstance(ver_data, dict):
            grounded_val = ver_data.get("grounded")
            conf_val = float(ver_data.get("confidence", 0.0))
            logger.info(
                "    [STATUTE_CORPUS] doc=%s cosine=%.6f llm_grounded=%s llm_conf=%.2f",
                doc_id, score, grounded_val, conf_val,
            )
            if grounded_val is True:
                logger.info(
                    "  [RESULT] GROUNDED via statute_corpus | source=%s cosine=%.6f | claim='%s'",
                    doc_id, score, claim_str,
                )
                return VerificationResult(
                    claim_id=claim_id,
                    source_risk_flag_id=flag_id,
                    claim_text=claim_str,
                    grounded=True,
                    supporting_source_id=doc_id,
                    grounding_source="statute_corpus",
                    raw_cosine_score=score,
                    confidence=conf_val,
                )

    logger.info("  [RESULT] UNVERIFIED (no doc passed LLM check) | claim='%s'", claim_str)
    return VerificationResult(
        claim_id=claim_id,
        source_risk_flag_id=flag_id,
        claim_text=claim_str,
        grounded=False,
        supporting_source_id=None,
        grounding_source="none",
        raw_cosine_score=best_score,
        confidence=0.0,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _parse_json(text: str) -> tuple[Any | None, str]:
    if not text.strip():
        return None, "empty response"
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        inner = lines[1:-1] if len(lines) > 2 else lines
        clean = "\n".join(inner).strip()
    try:
        return json.loads(clean), ""
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"


def _extract_doc_id(doc) -> str:
    return str(
        doc.metadata.get("_id")
        or doc.metadata.get("id")
        or doc.metadata.get("point_id")
        or getattr(doc, "id", None)
        or "unknown"
    )


def _unverified(claim_id: str, flag_id: str, claim_str: str) -> VerificationResult:
    return VerificationResult(
        claim_id=claim_id,
        source_risk_flag_id=flag_id,
        claim_text=claim_str,
        grounded=False,
        supporting_source_id=None,
        grounding_source="none",
        raw_cosine_score=None,
        confidence=0.0,
    )


def _get_vector_store(jurisdiction: str = "us_generic"):
    """Return a raw QdrantVectorStore for similarity_search_with_score access."""
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    if not qdrant_url or not qdrant_api_key:
        logger.warning("_get_vector_store: missing QDRANT credentials")
        return None
    collection_name = f"themis_{jurisdiction}"
    try:
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        embeddings = _get_embeddings()
        return QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings,
            content_payload_key="text",
        )
    except Exception as exc:
        logger.warning("_get_vector_store: failed to init for %s: %s", collection_name, exc)
        return None
