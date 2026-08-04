"""
schemas/contract.py — PydanticAI schemas for contract extraction.

ClauseBundle is the output contract for Agent 2 (ExtractionAgent).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ClauseType(str, Enum):
    """Legal clause type taxonomy. Extensible: add new types without breaking downstream."""
    INDEMNIFICATION = "indemnification"
    LIMITATION_OF_LIABILITY = "limitation_of_liability"
    PAYMENT_TERMS = "payment_terms"
    TERMINATION = "termination"
    GOVERNING_LAW = "governing_law"
    CONFIDENTIALITY = "confidentiality"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    FORCE_MAJEURE = "force_majeure"
    DISPUTE_RESOLUTION = "dispute_resolution"
    REPRESENTATIONS_WARRANTIES = "representations_warranties"
    OTHER = "other"


class Clause(BaseModel):
    """A single extracted, classified clause from a contract."""

    clause_id: str = Field(..., description="UUID4 identifying this clause within the session.")
    clause_type: ClauseType
    raw_text: str = Field(..., description="Original clause text (post-PII redaction).")
    page_number: Optional[int] = Field(default=None, description="Source PDF page, if extractable.")
    heading: Optional[str] = Field(default=None, description="Section heading above the clause.")
    word_count: int
    extraction_confidence: float = Field(ge=0.0, le=1.0)


class ClauseBundle(BaseModel):
    """Output schema for Agent 2: Extraction Agent. Collection of all extracted clauses."""

    contract_id: str = Field(..., description="UUID4 assigned to this contract document.")
    tenant_id: str
    total_pages: int
    total_clauses: int
    clauses: list[Clause]
    extraction_warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal issues during extraction (e.g., scanned pages, watermarks).",
    )


class ExtractedContract(BaseModel):
    """
    Lightweight contract record written to PostgreSQL after extraction.
    Not part of ThemisState — persisted separately for portfolio queries.
    """
    contract_id: str
    tenant_id: str
    filename: str
    upload_timestamp: str  # ISO 8601
    jurisdiction: str
    clause_count: int
    status: str  # "extracted" | "analyzed" | "verified" | "error"
