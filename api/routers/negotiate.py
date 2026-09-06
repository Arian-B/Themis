"""
api/routers/negotiate.py — Negotiation simulation endpoints.

Endpoints:
  POST /api/v1/negotiate
    Starts a negotiation simulation for a specific contract + clause.
    Accepts: {contract_id, clause_id, client_position: str}
    Returns:  {session_id} — simulation runs synchronously and returns transcript

  GET /api/v1/negotiate/{session_id}
    Returns completed NegotiationTranscript for a finished simulation.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies import TenantContext, get_current_tenant, get_graph
from schemas.negotiation import NegotiationTranscript, NegotiationTurn

router = APIRouter(prefix="/negotiate", tags=["negotiation"])

# In-memory session store for negotiation transcripts
# In production, this would be persisted to Supabase/PostgreSQL
_negotiation_sessions: dict[str, NegotiationTranscript] = {}


class NegotiateStartRequest(BaseModel):
    contract_id: str
    clause_id: str
    client_position: str


class NegotiateStartResponse(BaseModel):
    session_id: str


def _run_negotiation_for_flag(
    graph: Any,
    contract_id: str,
    clause_id: str,
    client_position: str,
    tenant_id: str,
) -> NegotiationTranscript:
    """
    Run the negotiation simulation for a specific clause by directly invoking
    the negotiation subgraph (same logic as run_negotiation_node but with
    custom client_position).
    """
    from langgraph.checkpoint.sqlite import SqliteSaver
    import sqlite3
    from graph.build import build_graph
    
    # Get the main graph state to retrieve contract data
    config = {"configurable": {"thread_id": contract_id}}
    state = graph.get_state(config)
    
    if not state.values:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    if state.values.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Find the flag matching the clause_id
    risk_flags = state.values.get("risk_analysis_result", [])
    target_flag = None
    for flag in risk_flags:
        if flag.get("clause_id") == clause_id:
            target_flag = flag
            break
    
    if not target_flag:
        raise HTTPException(status_code=404, detail="Risk flag not found for this clause_id")
    
    # Check if this flag has been accepted for negotiation
    human_override = state.values.get("human_override", {})
    overrides = human_override.get("overrides", []) if isinstance(human_override, dict) else []
    flag_index = None
    for i, flag in enumerate(state.values.get("risk_analysis_result", [])):
        if flag.get("clause_id") == clause_id:
            flag_index = i
            break
    
    if flag_index is None:
        raise HTTPException(status_code=400, detail="Clause not found in risk analysis")
    
    flag_reviewed = any(ov.get("flag_index") == flag_index and ov.get("status") == "accepted" for ov in overrides)
    if not flag_reviewed:
        raise HTTPException(status_code=400, detail="Flag has not been accepted for negotiation")
    
    # Get original clause text
    raw_text = ""
    ext_result = state.values.get("extraction_result", {}).get("clauses", [])
    for c in ext_result:
        if c.get("clause_id") == clause_id:
            raw_text = c.get("text", "")
            break
    
    # Run the negotiation subgraph with custom client position
    from agents.negotiation_simulation import negotiation_graph
    
    sub_state = {
        "clause_id": clause_id,
        "original_text": raw_text,
        "concern": f"{target_flag.get('concern', '')} Client position: {client_position}",
        "turns": []
    }
    
    # Run negotiation
    res = negotiation_graph.invoke(sub_state)
    
    outcome = res.get("outcome")
    turns = res.get("turns", [])
    
    if not outcome:
        if len(turns) >= 4:
            outcome = "max_turns_reached"
        else:
            outcome = "impasse"
    
    # Convert to NegotiationTranscript schema
    transcript = NegotiationTranscript(
        clause_id=clause_id,
        turns=[
            NegotiationTurn(
                turn_number=t.get("turn_number", i + 1),
                speaker=t.get("speaker", "proposer"),
                proposed_text=t.get("proposed_text", ""),
                rationale=t.get("rationale", ""),
            )
            for i, t in enumerate(turns)
        ],
        outcome=outcome,
    )
    
    return transcript


@router.post("", response_model=NegotiateStartResponse)
async def start_negotiation(
    payload: NegotiateStartRequest,
    tenant: TenantContext = Depends(get_current_tenant),
    graph: Any = Depends(get_graph),
):
    """
    Start a negotiation simulation for a specific clause in a contract.
    """
    transcript = _run_negotiation_for_flag(
        graph=graph,
        contract_id=payload.contract_id,
        clause_id=payload.clause_id,
        client_position=payload.client_position,
        tenant_id=tenant.tenant_id,
    )
    
    # Store session with generated session_id
    session_id = str(uuid.uuid4())
    _negotiation_sessions[session_id] = transcript
    
    return NegotiateStartResponse(session_id=session_id)


@router.get("/{session_id}", response_model=NegotiationTranscript)
async def get_negotiation_transcript(
    session_id: str,
    tenant: TenantContext = Depends(get_current_tenant),
    graph: Any = Depends(get_graph),
):
    """
    Retrieve a completed negotiation transcript by session ID.
    """
    transcript = _negotiation_sessions.get(session_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Negotiation session not found")
    
    return transcript