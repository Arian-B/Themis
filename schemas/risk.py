"""
schemas/risk.py — PydanticAI schemas for risk analysis and atomic verification.

RiskReport is the output contract for Agent 3 (RiskAnalysisAgent).
VerifiedRiskReport is the output contract for Agent 4 (AtomicVerificationAgent).

The distinction is deliberate and interview-worthy:
  - RiskReport: raw LLM output, NOT shown to user
  - VerifiedRiskReport: every assertion grounded in retrieved text, safe to display
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AtomicAssertion(BaseModel):
    """A single atomic fact decomposed from a risk rationale."""

    assertion_id: str
    assertion_text: str = Field(..., description="The atomic claim to be verified.")
    verified: bool = Field(..., description="True if grounded in retrieved source text.")
    source_chunk_id: Optional[str] = Field(
        default=None, description="Qdrant chunk ID that supports this assertion."
    )
    supporting_quote: Optional[str] = Field(
        default=None,
        description="Verbatim text from the source chunk that supports the assertion.",
    )
    verification_rationale: Optional[str] = Field(
        default=None,
        description="Claude's explanation of why the assertion is/is not supported.",
    )


class RiskItem(BaseModel):
    """Risk assessment for a single clause. Part of the unverified RiskReport."""

    clause_id: str
    clause_type: str
    risk_level: RiskLevel
    risk_rationale: str = Field(..., description="Full risk reasoning (may be unverified).")
    non_standard_language: list[str] = Field(
        default_factory=list,
        description="Exact phrases in the clause that deviate from market standard.",
    )
    suggested_redline: Optional[str] = None
    retrieved_source_ids: list[str] = Field(
        default_factory=list,
        description="Qdrant chunk IDs retrieved for this clause during analysis.",
    )
    confidence: float = Field(ge=0.0, le=1.0)


class RiskReport(BaseModel):
    """Output schema for Agent 3: Risk Analysis Agent. UNVERIFIED — internal use only."""

    contract_id: str
    tenant_id: str
    jurisdiction: str
    risk_items: list[RiskItem]
    overall_risk_level: RiskLevel
    analysis_model: str = Field(..., description="Model used (e.g., 'claude-3-5-sonnet-20241022').")


class VerifiedRiskItem(BaseModel):
    """A RiskItem where all atomic assertions have been verified against source text."""

    clause_id: str
    clause_type: str
    risk_level: RiskLevel
    verified_rationale: str = Field(
        ..., description="Risk rationale containing only verified assertions."
    )
    atomic_assertions: list[AtomicAssertion]
    verification_partial: bool = Field(
        default=False,
        description="True if some assertions were discarded; risk_level was downgraded.",
    )
    non_standard_language: list[str]
    suggested_redline: Optional[str]
    citations: list[str] = Field(
        ...,
        description="List of source chunk IDs + supporting quotes for frontend citation display.",
    )


class VerifiedRiskReport(BaseModel):
    """Output schema for Agent 4: Atomic Verification Agent. SAFE to display to user."""

    contract_id: str
    tenant_id: str
    jurisdiction: str
    verified_risk_items: list[VerifiedRiskItem]
    discarded_item_count: int = Field(
        ...,
        description="Number of RiskItems removed because assertions could not be verified.",
    )
    overall_risk_level: RiskLevel
    verification_model: str
