"""
tests/conftest.py — Shared pytest fixtures for the Themis test suite.

Organisation:
  tests/unit/        — Pure unit tests: no Docker services, no network calls.
                       Mock all LLM clients and DB connections.
  tests/integration/ — Integration tests: real Qdrant + Neo4j (via docker compose).
                       Use pytest-docker or a pre-started local stack.

Fixture strategy:
  - `themis_state_factory` — builds a valid ThemisState dict for a given phase
  - `mock_ollama_client`   — patches LangChain ChatOllama to return fixture responses
  - `mock_anthropic_client`— patches LangChain ChatAnthropic
  - `mock_qdrant_client`   — patches QdrantClient with in-memory vector store
  - `mock_neo4j_driver`    — patches Neo4j driver with a fake session
  - `test_pdf_bytes`       — returns a minimal valid PDF (generated, not stored)
  - `sample_clause_bundle` — a valid ClauseBundle for downstream agent tests
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# State fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_state() -> dict:
    """Minimal valid ThemisState for tests that don't need a full document."""
    return {
        "tenant_id": "test-tenant-001",
        "session_id": "00000000-0000-0000-0000-000000000001",
        "document_metadata": {"filename": "test_contract.pdf", "page_count": 5},
        "messages": [],
        "errors": [],
        "pending_human_review": False,
    }


@pytest.fixture
def sample_raw_text() -> str:
    """Minimal contract text with a governing law clause for classifier tests."""
    return (
        "SERVICE AGREEMENT\n\n"
        "This agreement is governed by and construed in accordance with the laws "
        "of the State of California, United States of America.\n\n"
        "1. INDEMNIFICATION\nEach party shall indemnify the other against all claims.\n\n"
        "2. LIMITATION OF LIABILITY\nIn no event shall either party's liability exceed "
        "the amounts paid in the preceding 12 months."
    )


# ---------------------------------------------------------------------------
# LLM mock fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ollama_response():
    """
    Factory fixture: returns a mock ChatOllama that produces a given JSON string.
    Usage: mock_ollama_response('{"jurisdiction": "us_generic", "confidence": 0.95, ...}')
    """
    def _factory(json_str: str):
        mock = MagicMock()
        mock.ainvoke = AsyncMock(return_value=MagicMock(content=json_str))
        return mock
    return _factory


@pytest.fixture
def mock_anthropic_response():
    """Factory fixture: mock ChatAnthropic returning a given JSON string."""
    def _factory(json_str: str):
        mock = MagicMock()
        mock.ainvoke = AsyncMock(return_value=MagicMock(content=json_str))
        return mock
    return _factory


# ---------------------------------------------------------------------------
# PDF fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_pdf_bytes() -> bytes:
    """
    Returns the bytes of a minimal valid single-page PDF containing sample
    contract text. Generated programmatically — no binary assets committed.
    TODO (Phase 1): Implement using reportlab or fpdf2.
    """
    # Placeholder: real implementation creates a proper PDF in memory
    return b"%PDF-1.4 minimal test fixture -- implement in Phase 1"
