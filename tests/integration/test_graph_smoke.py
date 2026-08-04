"""
tests/integration/test_graph_smoke.py — Integration smoke test for the LangGraph workflow.

Phase 1 target: proves the graph wires up, accepts a PDF, runs through all 3 nodes,
and returns a structured RiskReport — end-to-end without mocking the graph itself.

LLM calls ARE mocked (too slow + expensive for CI); retrieval IS mocked (Phase 2+).
Qdrant and Neo4j are NOT required for Phase 1 smoke test.

Test: POST /api/v1/contracts/analyze → poll /status → expect RiskReport JSON

TODO (Phase 1): Implement once workflow.py + contracts.py router are complete.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

# TODO (Phase 1): import app from api.main


@pytest.mark.skip(reason="Phase 1: implement after graph/workflow.py is complete")
@pytest.mark.asyncio
async def test_analyze_contract_returns_risk_report(minimal_pdf_bytes, base_state):
    """
    End-to-end smoke test:
      1. POST a minimal PDF to /analyze
      2. Receive session_id
      3. Poll /status until complete (or timeout)
      4. GET /contracts/{contract_id} and verify VerifiedRiskReport schema
    """
    # from api.main import app
    # async with AsyncClient(app=app, base_url="http://test") as client:
    #     response = await client.post(
    #         "/api/v1/contracts/analyze",
    #         files={"file": ("test.pdf", minimal_pdf_bytes, "application/pdf")},
    #         headers={"Authorization": "Bearer <test-jwt>"},
    #     )
    #     assert response.status_code == 202
    #     session_id = response.json()["session_id"]
    #     # ... poll and assert
    pass
