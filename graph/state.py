"""
graph/state.py — ThemisState: the single source of truth for the LangGraph state machine.

Every agent node in the Themis workflow reads from and writes to this TypedDict.
Keeping all mutable state here (rather than in agent-local objects) is what enables
LangGraph's checkpointing, human-in-the-loop interrupts, and graph replay.

Design invariants:
  - All fields are Optional so nodes can partially populate state without error.
  - Schema-validated payloads (PydanticAI models) are stored as dicts after
    `.model_dump()` so they survive LangGraph's JSON serialization round-trip.
  - `errors` is an append-only log; nodes must never clear it.
  - `tenant_id` is immutable after graph entry — never written by agent nodes.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional
from typing_extensions import TypedDict

from langgraph.graph import add_messages


class ThemisState(TypedDict, total=False):
    # ── Identity ──────────────────────────────────────────────────────────────
    tenant_id: str
    """Immutable tenant identifier — set at graph entry, used for namespace isolation."""

    session_id: str
    """Unique ID for this analysis session (UUID4). Used as Langfuse trace ID."""

    # ── Inbound document ──────────────────────────────────────────────────────
    raw_pdf_bytes: bytes
    """Raw bytes of the uploaded contract PDF. Cleared after extraction to save memory."""

    raw_text: str
    """Full extracted text of the contract before clause segmentation."""

    document_metadata: dict[str, Any]
    """Filename, upload timestamp, page count, MIME type, etc."""

    # ── Jurisdiction routing (Agent 1 output) ─────────────────────────────────
    jurisdiction_result: dict[str, Any]
    """Serialised JurisdictionResult schema. Includes detected jurisdiction + confidence."""

    # ── Extracted clauses (Agent 2 output) ────────────────────────────────────
    clause_bundle: dict[str, Any]
    """Serialised ClauseBundle schema. List of segmented, typed clauses."""

    # ── Risk analysis (Agent 3 output) ────────────────────────────────────────
    risk_report: dict[str, Any]
    """Serialised RiskReport schema. Unverified risk flags from the Risk Analysis Agent."""

    # ── Atomic verification (Agent 4 output) ──────────────────────────────────
    verified_risk_report: dict[str, Any]
    """Serialised VerifiedRiskReport. Only verified assertions; discarded ones logged."""

    # ── Knowledge graph write (Agent 5 output) ────────────────────────────────
    kg_write_result: dict[str, Any]
    """Serialised KGWriteResult. Confirms which entities/edges were written to Neo4j."""

    # ── Negotiation simulation (Agent 6 output) ───────────────────────────────
    negotiation_transcript: dict[str, Any]
    """Serialised NegotiationTranscript. Full adversarial redline exchange."""

    # ── Regulatory monitoring (Agent 7 output) ────────────────────────────────
    regulatory_alerts: list[dict[str, Any]]
    """List of serialised RegulatoryAlert schemas detected for this contract."""

    # ── Human-in-the-loop ─────────────────────────────────────────────────────
    human_override: Optional[dict[str, Any]]
    """Populated by the HITL interrupt when a human reviewer overrides an agent decision."""

    pending_human_review: bool
    """Flag set by any agent that requires human approval before proceeding."""

    # ── Conversation / streaming messages ────────────────────────────────────
    messages: Annotated[list[dict[str, Any]], add_messages]
    """Append-only message log. Used for streaming partial results to the frontend."""

    # ── Control flow ──────────────────────────────────────────────────────────
    current_node: str
    """Name of the node currently executing. Set at node entry for observability."""

    next_node: Optional[str]
    """Override the next routing decision. Set by conditional edge functions."""

    # ── Error handling ────────────────────────────────────────────────────────
    errors: list[dict[str, Any]]
    """Append-only list of {node, error_type, message, timestamp} records."""
