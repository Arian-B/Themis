import os
import uuid
from typing import Any
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from api.dependencies import get_current_tenant, TenantContext, get_graph

router = APIRouter(prefix="/contracts", tags=["contracts"])

import logging
import requests as _requests_module

logger = logging.getLogger(__name__)


def _flag_requires_human_review(flag: dict[str, Any], verification_results: list[dict[str, Any]]) -> bool:
    """Apply the same high-risk/grounding rule used by the CLI review workflow."""
    flag_id = f"{flag.get('clause_id', '')}_risk"
    flag_claims = [
        result
        for result in verification_results
        if result.get("source_risk_flag_id") == flag_id
    ]
    is_ungrounded = not flag_claims or any(
        not result.get("grounded", False) for result in flag_claims
    )
    is_high_risk = flag.get("risk_level", "").lower() == "high"
    return is_high_risk or is_ungrounded


def _flag_is_grounded(flag: dict[str, Any], verification_results: list[dict[str, Any]]) -> bool:
    flag_id = f"{flag.get('clause_id', '')}_risk"
    flag_claims = [
        result
        for result in verification_results
        if result.get("source_risk_flag_id") == flag_id
    ]
    return bool(flag_claims) and all(result.get("grounded", False) for result in flag_claims)


def _enrich_flag_with_grounded(flag: dict[str, Any], verification_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a shallow copy of the risk flag with a computed `grounded` boolean.

    The RiskFlag schema (schemas/risk.py) does not carry a `grounded` field —
    that lives on VerificationResult — so API consumers must be given a
    pre-computed aggregate per-flag boolean that matches
    _flag_requires_human_review / scripts/resume_review.py.
    """
    enriched = dict(flag)
    enriched["grounded"] = _flag_is_grounded(flag, verification_results)
    return enriched


def _is_flag_reviewed(state: dict, flag_index: int) -> bool:
    """Check if a flag at the given index has already been reviewed by a human."""
    human_override = state.get("human_override", {})
    overrides = human_override.get("overrides", []) if isinstance(human_override, dict) else []
    return any(ov.get("flag_index") == flag_index for ov in overrides)


def log_audit_event(tenant_id: str, action: str, resource_type: str, resource_id: str, details: dict):
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.warning("Missing Supabase credentials, skipping audit log.")
        return

    endpoint = f"{url}/rest/v1/audit_log"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    payload = {
        "tenant_id": tenant_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details
    }
    try:
        import requests
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=5)
        if resp.status_code >= 400:
            logger.error(f"Failed to write to audit_log: {resp.text}")
    except Exception as e:
        logger.error(f"Error calling Supabase: {e}")

def run_pipeline(thread_id: str, file_path: str, tenant_id: str, graph: Any):
    config = {"configurable": {"thread_id": thread_id}}

    # Pre-flight: verify Ollama is accessible (extraction_agent uses ChatOllama)
    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    try:
        health = _requests_module.get(f"{ollama_host}/api/tags", timeout=5)
        if health.status_code != 200:
            logger.error(f"run_pipeline [{thread_id}]: Ollama health check failed with status {health.status_code}. Extraction will produce 0 clauses.")
    except Exception as e:
        logger.error(f"run_pipeline [{thread_id}]: Ollama is not reachable at {ollama_host}: {e}. Extraction will produce 0 clauses.")

    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
        
    res = graph.invoke({"raw_text": raw_text, "tenant_id": tenant_id, "session_id": thread_id, "contract_id": thread_id}, config)
    
    # Diagnostic: log state contents at completion to surface silent failures
    n_clauses = len((res.get("extraction_result") or {}).get("clauses", []))
    n_risk = len(res.get("risk_analysis_result") or [])
    n_ver = len(res.get("verification_result") or [])
    logger.info(f"run_pipeline [{thread_id}]: graph.invoke complete. clauses={n_clauses}, risk_flags={n_risk}, verification={n_ver}")

    high_risk_flags = []
    verification_results = res.get("verification_result", [])
    for flag in res.get("risk_analysis_result", []):
        if _flag_requires_human_review(flag, verification_results):
            high_risk_flags.append({
                "clause_id": flag.get("clause_id"),
                "concern": flag.get("concern"),
                "risk_level": flag.get("risk_level"),
                "grounded": _flag_is_grounded(flag, verification_results),
            })

    if high_risk_flags:
        for flag in high_risk_flags:
            logger.warning(f"HIGH RISK FLAG: {flag.get('clause_id')} - {flag.get('concern')}")

@router.post("/upload")
async def upload_contract(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tenant: TenantContext = Depends(get_current_tenant),
    graph: Any = Depends(get_graph)
):
    thread_id = str(uuid.uuid4())
    upload_dir = os.path.join("data", "raw")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{thread_id}.txt")
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
        
    background_tasks.add_task(run_pipeline, thread_id, file_path, tenant.tenant_id, graph)
    return {"contract_id": thread_id, "status": "processing"}

@router.get("/{contract_id}/status")
async def get_contract_status(contract_id: str, tenant: TenantContext = Depends(get_current_tenant), graph: Any = Depends(get_graph)):
    config = {"configurable": {"thread_id": contract_id}}
    state = graph.get_state(config)
    if not state.values:
        return {"status": "processing"}
    if state.values.get("tenant_id") != tenant.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if "human_review" in state.next:
        return {"status": "awaiting_review"}
    if not state.next:
        return {"status": "complete"}
    return {"status": "processing"}

@router.get("/{contract_id}/results")
async def get_contract_results(contract_id: str, tenant: TenantContext = Depends(get_current_tenant), graph: Any = Depends(get_graph)):
    config = {"configurable": {"thread_id": contract_id}}
    state = graph.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Not Found")
    if state.values.get("tenant_id") != tenant.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    verification_results = state.values.get("verification_result", [])
    raw_flags = state.values.get("risk_analysis_result", []) or []
    enriched_flags = [
        _enrich_flag_with_grounded(
            f if isinstance(f, dict) else f.model_dump(),
            verification_results,
        )
        for f in raw_flags
    ]
    return {
        "jurisdiction": state.values.get("jurisdiction_result"),
        "clauses": state.values.get("extraction_result", {}).get("clauses", []),
        "risk_flags": enriched_flags,
    }

@router.get("/{contract_id}/review-queue")
async def get_review_queue(contract_id: str, tenant: TenantContext = Depends(get_current_tenant), graph: Any = Depends(get_graph)):
    config = {"configurable": {"thread_id": contract_id}}
    state = graph.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Not Found")
    if state.values.get("tenant_id") != tenant.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    verification_results = state.values.get("verification_result", [])
    raw_flags = state.values.get("risk_analysis_result", []) or []
    queue = [
        _enrich_flag_with_grounded(
            f if isinstance(f, dict) else f.model_dump(),
            verification_results,
        )
        for i, f in enumerate(raw_flags)
        if _flag_requires_human_review(
            f if isinstance(f, dict) else f.model_dump(),
            verification_results,
        )
        and not _is_flag_reviewed(state.values, i)
    ]
    return {"queue": queue}

def resume_pipeline(thread_id: str, graph: Any) -> None:
    """Resume a graph after the reviewer has updated its paused state."""
    graph.invoke(None, {"configurable": {"thread_id": thread_id}})


@router.post("/{contract_id}/review")
async def submit_review(
    contract_id: str,
    payload: dict,
    background_tasks: BackgroundTasks,
    tenant: TenantContext = Depends(get_current_tenant),
    graph: Any = Depends(get_graph),
):
    config = {"configurable": {"thread_id": contract_id}}
    state = graph.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Not Found")
    if state.values.get("tenant_id") != tenant.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    decision = payload.get("decision")
    flag_id = payload.get("flag_id")

    risk_flags = state.values.get("risk_analysis_result", [])
    flag_index = next(
        (
            index
            for index, flag in enumerate(risk_flags)
            if flag.get("clause_id") == flag_id
        ),
        None,
    )
    if flag_index is None:
        raise HTTPException(status_code=404, detail="Risk flag not found for this contract")

    graph.update_state(
        config,
        {
            "human_override": {
                "overrides": [{"flag_index": flag_index, "status": decision}]
            },
            "pending_human_review": False,
        },
        as_node="human_review",
    )

    # Log the decision to Supabase audit_log
    flag_details = {}
    if risk_flags:
        for f in risk_flags:
            # Depending on if it's a dict or Pydantic model
            fid = f.get("clause_id") if isinstance(f, dict) else getattr(f, "clause_id", None)
            if fid == flag_id:
                flag_details = {
                    "concern": f.get("concern") if isinstance(f, dict) else getattr(f, "concern", "Unknown"),
                    "original_risk": f.get("risk_level") if isinstance(f, dict) else getattr(f, "risk_level", "Unknown")
                }
                break

    action = "flag.accepted" if decision == "accepted" else "flag.overridden"
    details = {
        "contract_id": contract_id,
        "concern": flag_details.get("concern", "Unknown concern"),
        "human_override": decision,
        "original_risk": flag_details.get("original_risk", "Unknown")
    }
    log_audit_event(tenant.tenant_id, action, "risk_flag", flag_id, details)
    background_tasks.add_task(resume_pipeline, contract_id, graph)

    return {"status": "review_submitted", "flag_id": flag_id, "decision": decision}
