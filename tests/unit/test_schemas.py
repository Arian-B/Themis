"""
tests/unit/test_schemas.py — Unit tests for all PydanticAI schema models.

These tests verify that:
  1. Valid data is accepted and round-trips correctly via .model_dump() / .model_validate()
  2. Invalid data raises ValidationError with meaningful messages
  3. Enum values are correctly constrained
  4. Optional fields default correctly

No LLM calls, no Docker services required.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas.jurisdiction import Jurisdiction, JurisdictionResult
from schemas.contract import Clause, ClauseBundle, ClauseType
from schemas.risk import AtomicAssertion, RiskItem, RiskLevel, RiskReport, VerifiedRiskReport
from schemas.negotiation import NegotiationTranscript, Redline, RedlineSide
from schemas.knowledge_graph import Entity, EntityType, KGWriteResult
from schemas.feedback import CorrectionRecord, HumanOverride


class TestJurisdictionResult:
    def test_valid_us_generic(self):
        result = JurisdictionResult(
            jurisdiction=Jurisdiction.US_GENERIC,
            confidence=0.95,
            governing_law_clause_text="governed by the laws of California",
            fallback_used=False,
            rationale="Governing law clause explicitly references United States law.",
        )
        assert result.jurisdiction == Jurisdiction.US_GENERIC
        assert result.confidence == 0.95

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            JurisdictionResult(
                jurisdiction=Jurisdiction.UK,
                confidence=1.5,  # > 1.0 — invalid
                rationale="test",
            )

    def test_round_trip_serialisation(self):
        result = JurisdictionResult(
            jurisdiction=Jurisdiction.UK,
            confidence=0.88,
            rationale="UK governing law clause found.",
        )
        dumped = result.model_dump()
        restored = JurisdictionResult.model_validate(dumped)
        assert restored == result


class TestClauseBundle:
    def test_empty_clause_list_is_valid(self):
        bundle = ClauseBundle(
            contract_id="test-id-001",
            tenant_id="tenant-abc",
            total_pages=1,
            total_clauses=0,
            clauses=[],
        )
        assert bundle.total_clauses == 0

    def test_clause_type_enum_validation(self):
        with pytest.raises(ValidationError):
            Clause(
                clause_id="c1",
                clause_type="invalid_type",  # not in ClauseType enum
                raw_text="test clause",
                word_count=2,
                extraction_confidence=0.9,
            )


class TestRiskSchemas:
    def test_risk_level_ordering_semantics(self):
        """Verify all RiskLevel values are present and distinct."""
        levels = {r.value for r in RiskLevel}
        assert levels == {"low", "medium", "high", "critical"}

    def test_atomic_assertion_unverified_by_default(self):
        assertion = AtomicAssertion(
            assertion_id="a1",
            assertion_text="Liability is uncapped.",
            verified=False,
        )
        assert assertion.source_chunk_id is None
        assert assertion.supporting_quote is None


# TODO (Phase 1): Add tests for RiskReport, VerifiedRiskReport serialisation
# TODO (Phase 3): Add tests for NegotiationTranscript, KGWriteResult
