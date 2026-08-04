"""
schemas/negotiation.py — PydanticAI schemas for negotiation simulation.

NegotiationTranscript is the output contract for Agent 6 (NegotiationSimulationAgent).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RedlineSide(str, Enum):
    PROPOSER = "proposer"  # Our client's counsel
    CRITIC = "critic"      # Counterparty's counsel


class Redline(BaseModel):
    """A single turn in the adversarial negotiation exchange."""

    turn_number: int
    side: RedlineSide
    original_text: Optional[str] = Field(
        default=None, description="The clause text being redlined (set on turn 1 only)."
    )
    proposed_text: str = Field(..., description="The proposed replacement clause language.")
    rationale: str = Field(..., description="Legal rationale for the proposed change.")
    acceptable: bool = Field(
        ..., description="Whether this side marks the current proposal as acceptable."
    )


class NegotiationOutcome(str, Enum):
    AGREED = "agreed"
    IMPASSE = "impasse"
    MAX_ROUNDS_REACHED = "max_rounds_reached"


class ClauseNegotiation(BaseModel):
    """Negotiation result for a single clause."""

    clause_id: str
    clause_type: str
    original_risk_level: str
    redlines: list[Redline]
    outcome: NegotiationOutcome
    final_agreed_text: Optional[str] = Field(
        default=None, description="Agreed clause text if outcome == AGREED."
    )
    rounds_taken: int


class NegotiationTranscript(BaseModel):
    """Output schema for Agent 6: Negotiation Simulation Agent."""

    contract_id: str
    tenant_id: str
    clause_negotiations: list[ClauseNegotiation]
    total_clauses_negotiated: int
    agreed_count: int
    impasse_count: int
    negotiation_model: str
