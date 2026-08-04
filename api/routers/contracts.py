"""
api/routers/contracts.py — Contract analysis endpoints.

Endpoints:
  POST /api/v1/contracts/analyze
    Accepts a PDF file upload + optional metadata.
    Runs the full Themis LangGraph workflow.
    Returns session_id immediately (async); client polls /status/{session_id}
    OR connects to WebSocket /ws/{session_id} for streaming updates.

  GET /api/v1/contracts/{contract_id}
    Returns the stored ExtractedContract + VerifiedRiskReport for a contract.
    Requires tenant_id match (from JWT).

  GET /api/v1/contracts/{contract_id}/status
    Returns current graph node + completion percentage for async polling.

  POST /api/v1/contracts/{session_id}/override
    Accepts a HumanOverride body; resumes the LangGraph interrupt.
    This is the HITL endpoint — called when a reviewer disagrees with a risk flag.

Multi-tenancy:
  All endpoints extract tenant_id from JWT via Depends(get_current_tenant).
  The graph is invoked with config={"configurable": {"thread_id": session_id,
  "tenant_id": tenant_id}} — LangGraph uses this for checkpoint namespace isolation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File

router = APIRouter(prefix="/contracts", tags=["contracts"])

# TODO (Phase 1): Implement /analyze endpoint:
#   1. Receive PDF upload
#   2. Generate contract_id (UUID4) + session_id
#   3. Build initial ThemisState with raw_pdf_bytes + tenant_id + session_id
#   4. Invoke graph.astream() with interrupt_before config
#   5. Return {"session_id": session_id, "contract_id": contract_id}

# TODO (Phase 1): Implement /status endpoint (simple poll for MVP)
# TODO (Phase 4): Add WebSocket streaming endpoint
# TODO (Phase 4): Implement /override HITL endpoint
