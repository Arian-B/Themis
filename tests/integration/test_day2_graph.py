"""
tests/integration/test_day2_graph.py — Integration test for the Day 2 LangGraph pipeline.

Tests the full graph end-to-end on the SaaS MSA from the Day 1 corpus:
  START → jurisdiction_classifier → extraction_agent → END

What is tested:
  1. Graph runs without uncaught exceptions
  2. jurisdiction_result is not None and confidence > 0
  3. jurisdiction is one of the supported values ("us_generic", "uk")
  4. extraction_result contains at least 5 clauses
  5. All clauses have valid clause_type values from the enum

Prerequisites:
  - Ollama must be running with llama3.1:8b pulled
  - data/raw/themis_edgar_contracts.jsonl must exist (from Day 1 pipeline)
  - OLLAMA_HOST set in .env or environment

Runtime: ~60–120 seconds (one Ollama inference per clause + jurisdiction call).
Marked with @pytest.mark.integration and @pytest.mark.slow.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

# Load .env before any project imports
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_CLAUSE_TYPES = {
    "termination",
    "payment_terms",
    "liability",
    "auto_renewal",
    "non_compete",
    "indemnification",
    "confidentiality",
    "other",
}

VALID_JURISDICTIONS = {"us_generic", "uk"}

EDGAR_PATH = ROOT / "data" / "raw" / "themis_edgar_contracts.jsonl"


@pytest.fixture(scope="module")
def saas_msa_text() -> str:
    """Load the SaaS MSA text from the Day 1 corpus."""
    if not EDGAR_PATH.exists():
        pytest.skip(f"EDGAR corpus not found at {EDGAR_PATH} — run the ingestion pipeline first")
    docs = [json.loads(l) for l in EDGAR_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert docs, "themis_edgar_contracts.jsonl is empty"
    return docs[0]["text"]  # index 0 = SaaS MSA


@pytest.fixture(scope="module")
def saas_msa_doc_id() -> str:
    """Return the doc_id of the SaaS MSA."""
    docs = [json.loads(l) for l in EDGAR_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    return docs[0]["doc_id"]


@pytest.fixture(scope="module")
def graph_result(saas_msa_text, saas_msa_doc_id):
    """
    Run the full Day 2 graph on the SaaS MSA. Module-scoped so we only hit
    Ollama once for the entire test session (avoids 3-minute timeouts per test).
    """
    if not os.getenv("OLLAMA_HOST"):
        pytest.skip("OLLAMA_HOST not set — skipping live Ollama test")

    from graph.build import build_graph
    from graph.state import ThemisState

    graph = build_graph()
    initial_state: ThemisState = {
        "contract_id": saas_msa_doc_id,
        "tenant_id": "test_tenant",
        "session_id": str(uuid.uuid4()),
        "raw_text": saas_msa_text,
        "errors": [],
    }
    return graph.invoke(initial_state)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.slow
class TestDay2Graph:

    def test_graph_completes_without_exception(self, graph_result):
        """The graph must return a result dict without raising."""
        assert graph_result is not None, "Graph returned None"
        assert isinstance(graph_result, dict), "Graph result must be a dict"

    def test_jurisdiction_result_present(self, graph_result):
        """jurisdiction_result must be populated after Agent 1 runs."""
        jur = graph_result.get("jurisdiction_result")
        assert jur is not None, "jurisdiction_result is None — Agent 1 did not run"
        assert isinstance(jur, dict), f"jurisdiction_result must be a dict, got {type(jur)}"

    def test_jurisdiction_confidence_positive(self, graph_result):
        """Confidence must be > 0 (0 only on permanent error with fallback)."""
        jur = graph_result["jurisdiction_result"]
        confidence = jur.get("confidence", 0)
        assert confidence > 0, (
            f"confidence={confidence} — did the model fail completely? "
            f"reasoning={jur.get('reasoning')}"
        )

    def test_jurisdiction_value_valid(self, graph_result):
        """Jurisdiction must be one of the supported values."""
        jur = graph_result["jurisdiction_result"]
        jurisdiction = jur.get("jurisdiction")
        assert jurisdiction in VALID_JURISDICTIONS, (
            f"jurisdiction='{jurisdiction}' not in {VALID_JURISDICTIONS}"
        )

    def test_jurisdiction_reasoning_non_empty(self, graph_result):
        """Reasoning field must be a non-empty string."""
        jur = graph_result["jurisdiction_result"]
        reasoning = jur.get("reasoning", "")
        assert isinstance(reasoning, str) and len(reasoning.strip()) > 10, (
            f"reasoning is too short or empty: '{reasoning}'"
        )

    def test_extraction_result_present(self, graph_result):
        """extraction_result must be populated after Agent 2 runs."""
        ext = graph_result.get("extraction_result")
        assert ext is not None, "extraction_result is None — Agent 2 did not run"
        assert isinstance(ext, dict), f"extraction_result must be a dict, got {type(ext)}"

    def test_extraction_at_least_five_clauses(self, graph_result):
        """The SaaS MSA must yield at least 5 clauses."""
        ext = graph_result["extraction_result"]
        clauses = ext.get("clauses", [])
        assert len(clauses) >= 5, (
            f"Only {len(clauses)} clauses extracted — expected >= 5. "
            "Check extraction_agent segmentation logic."
        )

    def test_all_clause_types_valid(self, graph_result):
        """Every extracted clause must have a valid clause_type."""
        ext = graph_result["extraction_result"]
        clauses = ext.get("clauses", [])
        for i, clause in enumerate(clauses):
            ct = clause.get("clause_type")
            assert ct in VALID_CLAUSE_TYPES, (
                f"Clause {i} has invalid clause_type='{ct}'. "
                f"Valid types: {VALID_CLAUSE_TYPES}"
            )

    def test_all_clauses_have_text(self, graph_result):
        """Every extracted clause must have non-empty text."""
        ext = graph_result["extraction_result"]
        clauses = ext.get("clauses", [])
        for i, clause in enumerate(clauses):
            text = clause.get("text", "")
            assert len(text.strip()) > 0, f"Clause {i} has empty text"

    def test_all_clauses_have_section_reference(self, graph_result):
        """Every extracted clause must have a non-empty section_reference."""
        ext = graph_result["extraction_result"]
        clauses = ext.get("clauses", [])
        for i, clause in enumerate(clauses):
            ref = clause.get("section_reference", "")
            assert len(ref.strip()) > 0, f"Clause {i} has empty section_reference"

    def test_no_critical_errors(self, graph_result):
        """
        The errors list should be empty for a clean run on the SaaS MSA.
        Individual segment failures are logged but should not prevent other clauses.
        """
        errors = graph_result.get("errors") or []
        # Allow segment-level classification failures (partial results OK)
        # but fail if there is a critical pipeline error (empty raw_text, etc.)
        critical = [e for e in errors if e.get("error_type") in ("ValueError", "RuntimeError")]
        assert not critical, (
            f"Critical errors in pipeline: {[e['message'] for e in critical]}"
        )
