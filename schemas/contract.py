"""
schemas/contract.py — Pydantic schemas for contract extraction (Agent 2).

ExtractionResult is the output contract for the extraction_agent node.
ClauseBundle is the richer legacy schema used for downstream agents (Risk Analysis,
KG Writer, etc.) — kept intact so those stubs don't break at import time.

Clause types supported (extensible via ClauseType enum):
  termination | payment_terms | liability | auto_renewal | non_compete |
  indemnification | confidentiality | other
"""

from __future__ import annotations

from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Day 2 schemas: used by ExtractionAgent (Agent 2)
# ---------------------------------------------------------------------------

class ExtractedClause(BaseModel):
    """A single extracted, classified clause from a contract."""

    clause_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="UUID4 identifying this clause within the extraction session.",
    )
    clause_type: Literal[
        "termination",
        "payment_terms",
        "liability",
        "auto_renewal",
        "non_compete",
        "indemnification",
        "confidentiality",
        "ip_ownership",
        "data_protection",
        "representations_warranties",
        "account_admin",
        "other",
    ] = Field(..., description="Legal clause category.")
    text: str = Field(..., description="Full verbatim text of the clause (post-PII redaction).")
    section_reference: str = Field(
        ...,
        description=(
            "Section number or heading where the clause appears "
            "(e.g. '3.1 Fees', 'Section 9 — Termination')."
        ),
    )


class ExtractionResult(BaseModel):
    """Output schema for Agent 2: Extraction Agent."""

    contract_id: str = Field(
        ...,
        description="Identifier for the contract being extracted.",
    )
    clauses: list[ExtractedClause] = Field(
        ...,
        description="All clauses extracted from the contract, in order of appearance.",
    )


# ---------------------------------------------------------------------------
# Legacy schemas — used by Agent 3+ stubs (kept for import compatibility)
# ---------------------------------------------------------------------------

class ClauseType(str):
    """Legacy clause type — superseded by ExtractedClause.clause_type Literal."""
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
    """Legacy clause schema — kept for Agent 3+ stubs."""

    clause_id: str = Field(default_factory=lambda: str(uuid4()))
    clause_type: str
    raw_text: str
    page_number: Optional[int] = None
    heading: Optional[str] = None
    word_count: int = 0
    extraction_confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ClauseBundle(BaseModel):
    """Legacy output schema for Agent 2 — superseded by ExtractionResult for Day 2."""

    contract_id: str
    tenant_id: str
    total_pages: int = 0
    total_clauses: int = 0
    clauses: list[Clause] = Field(default_factory=list)
    extraction_warnings: list[str] = Field(default_factory=list)


class ExtractedContract(BaseModel):
    """Lightweight contract record written to PostgreSQL after extraction."""
    contract_id: str
    tenant_id: str
    filename: str
    upload_timestamp: str  # ISO 8601
    jurisdiction: str
    clause_count: int
    status: str  # "extracted" | "analyzed" | "verified" | "error"
