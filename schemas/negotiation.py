"""
schemas/negotiation.py — PydanticAI schemas for negotiation simulation.

NegotiationTranscript is the output contract for Agent 6 (NegotiationSimulationAgent).
"""

from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field

class NegotiationTurn(BaseModel):
    """A single turn in the adversarial negotiation exchange."""
    turn_number: int
    speaker: Literal["proposer", "counterparty"]
    proposed_text: str = Field(..., description="The proposed clause language.")
    rationale: str = Field(..., description="Legal rationale for the proposed change.")


class NegotiationTranscript(BaseModel):
    """Output schema for Agent 6: Negotiation Simulation Agent."""
    clause_id: str
    turns: list[NegotiationTurn]
    outcome: Literal["agreement_reached", "impasse", "max_turns_reached"]
