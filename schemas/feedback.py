"""
schemas/feedback.py — PydanticAI schemas for human-in-the-loop feedback.

HumanOverride is populated by the HITL interrupt mechanism in LangGraph.
CorrectionRecord is the persistent form written to PostgreSQL.
CriticFeedback is the output from the Critic Agent (Day 6).
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class HumanOverride(BaseModel):
    """
    Submitted by a human reviewer via POST /contracts/{id}/override when they
    disagree with an agent's output. Resumes the LangGraph interrupt.
    """
    session_id: str
    overridden_node: str = Field(..., description="Name of the agent node being overridden.")
    original_output: dict[str, Any] = Field(..., description="The agent's original decision.")
    corrected_output: dict[str, Any] = Field(..., description="The human's corrected version.")
    override_reason: str = Field(..., description="Free-text justification from the reviewer.")
    reviewer_id: str
    timestamp: str  # ISO 8601


class CorrectionRecord(BaseModel):
    """
    Persisted to PostgreSQL after the Critic/Feedback Agent processes a HumanOverride.
    Used for threshold tuning and false-positive rate reduction.
    """
    record_id: str
    tenant_id: str
    session_id: str
    overridden_node: str
    clause_id: Optional[str] = None
    original_risk_level: Optional[str] = None
    corrected_risk_level: Optional[str] = None
    override_reason: str
    reviewer_id: str
    timestamp: str
    processed: bool = False


class CriticFeedback(BaseModel):
    """
    Output from the Critic Agent (Day 6).
    """
    flag_id: str
    human_decision: str
    was_flag_useful: bool
    lesson: str
