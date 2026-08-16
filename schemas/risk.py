"""
schemas/risk.py — Pydantic schemas for Risk Analysis and Atomic Verification.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class RiskFlag(BaseModel):
    """
    Identifies a specific legal or commercial risk within an extracted clause.
    """
    clause_id: str = Field(..., description="The ID of the ExtractedClause this risk was found in.")
    risk_level: Literal["low", "medium", "high"] = Field(..., description="Severity of the risk.")
    concern: str = Field(..., description="Plain-language explanation of the risk, omitting legal jargon.")
    retrieved_source_ids: list[str] = Field(
        default_factory=list,
        description="List of Qdrant point IDs that were used as grounding context to identify this risk."
    )
    reasoning: str = Field(..., description="Step-by-step reasoning explaining why this is a risk.")


class AtomicClaim(BaseModel):
    """
    A single, decomposed factual assertion extracted from a broader risk concern.
    Used for atomic verification against the corpus.
    """
    claim_id: str = Field(..., description="Unique ID for this atomic claim.")
    source_risk_flag_id: str = Field(..., description="The ID of the parent RiskFlag.")
    claim_text: str = Field(..., description="A single, independent factual assertion.")


class VerificationResult(BaseModel):
    """
    The result of verifying an AtomicClaim against the contract text or statute corpus.
    """
    claim_id: str = Field(..., description="The ID of the AtomicClaim being verified.")
    source_risk_flag_id: str = Field(..., description="The ID of the parent RiskFlag.")
    claim_text: str = Field(..., description="The text of the atomic claim being verified.")
    grounded: bool = Field(..., description="True if the claim is unequivocally supported by the source text.")
    supporting_source_id: Optional[str] = Field(
        None,
        description="The source ID of the chunk that supports the claim. "
                    "For contract_text grounding this is the clause_id; "
                    "for statute_corpus this is the Qdrant point ID.",
    )
    grounding_source: Literal["contract_text", "statute_corpus", "none"] = Field(
        "none",
        description="Which source grounded this claim: "
                    "'contract_text' = verified directly against the clause's own extracted text; "
                    "'statute_corpus' = verified against the Qdrant statute/template corpus; "
                    "'none' = unverified.",
    )
    raw_cosine_score: Optional[float] = Field(
        None,
        description="Raw Qdrant cosine similarity score for the top retrieved chunk. "
                    "None if grounded via contract_text (no embedding search) or retrieval empty.",
    )
    confidence: float = Field(
        0.0,
        description="LLM self-reported confidence when grounding_source='statute_corpus'. "
                    "Always 1.0 when grounding_source='contract_text'. 0.0 when unverified.",
    )
