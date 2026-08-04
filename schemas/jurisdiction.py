"""
schemas/jurisdiction.py — PydanticAI schemas for jurisdiction classification.

Every agent boundary in Themis uses PydanticAI models, not free-text dicts.
This ensures: (1) schema validation at the LLM output boundary, (2) type-safe
state reads in downstream agents, (3) automatic JSON serialisation via .model_dump().

JurisdictionResult is the output contract for Agent 1 (JurisdictionClassifierAgent).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Jurisdiction(str, Enum):
    """Supported jurisdictions. Pluggable: add new values + a corpus collection."""
    US_GENERIC = "us_generic"
    UK = "uk"
    UNKNOWN = "unknown"
    # Future: EU_GDPR = "eu_gdpr", CA_PIPEDA = "ca_pipeda"


class JurisdictionResult(BaseModel):
    """Output schema for Agent 1: Jurisdiction Classifier."""

    jurisdiction: Jurisdiction = Field(
        ...,
        description="Detected governing-law jurisdiction of the contract.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence in the jurisdiction classification (0–1).",
    )
    governing_law_clause_text: Optional[str] = Field(
        default=None,
        description="Verbatim text of the governing law clause if found, else None.",
    )
    fallback_used: bool = Field(
        default=False,
        description="True if jurisdiction fell back to us_generic due to UNKNOWN result.",
    )
    rationale: str = Field(
        ...,
        description="One-sentence explanation of how the jurisdiction was determined.",
    )
