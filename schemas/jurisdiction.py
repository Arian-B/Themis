"""
schemas/jurisdiction.py — PydanticAI schemas for jurisdiction classification.

Every agent boundary in Themis uses Pydantic models, not free-text dicts.
This ensures: (1) schema validation at the LLM output boundary, (2) type-safe
state reads in downstream agents, (3) automatic JSON serialisation via .model_dump().

JurisdictionClassification is the output contract for Agent 1 (jurisdiction_classifier).
JurisdictionResult is the legacy alias kept for backward compatibility.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class JurisdictionClassification(BaseModel):
    """
    Output schema for Agent 1: Jurisdiction Classifier.

    The LLM is instructed to produce a JSON object matching this schema.
    PydanticAI validates the output; on failure the agent retries once with
    an error-correction prompt before recording to state.errors.
    """

    jurisdiction: Literal["us_generic", "uk"] = Field(
        ...,
        description=(
            "Detected governing-law jurisdiction. 'us_generic' for US law "
            "(any state unless clearly UK), 'uk' for English/Welsh/Scottish law."
        ),
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence in the classification (0=no idea, 1=certain).",
    )
    reasoning: str = Field(
        ...,
        description=(
            "One-to-three sentence explanation of how the jurisdiction was determined, "
            "citing specific contract language if found."
        ),
    )
    governing_law_clause_text: Optional[str] = Field(
        default=None,
        description="Verbatim text of the governing-law clause if explicitly found, else None.",
    )
    fallback_used: bool = Field(
        default=False,
        description="True if the model fell back to 'us_generic' due to ambiguity.",
    )


# Backward-compat alias used elsewhere in the codebase
JurisdictionResult = JurisdictionClassification
