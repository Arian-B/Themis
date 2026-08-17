import os
import uuid
import json
import requests
from typing import Any
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from api.dependencies import get_current_tenant, TenantContext, get_graph
from langgraph.checkpoint.sqlite import SqliteSaver

router = APIRouter(prefix="/contracts", tags=["contracts"])

def run_pipeline(thread_id: str, file_path: str, tenant_id: str, graph: Any):
    config = {"configurable": {"thread_id": thread_id}}
    
    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
        
    res = graph.invoke({"raw_text": raw_text, "tenant_id": tenant_id, "session_id": thread_id, "contract_id": thread_id}, config)
    
    # Check for high risk flags
    high_risk_flags = []
    if "risk_analysis_result" in res:
        for flag in res["risk_analysis_result"]:
            is_unverified = flag.get("is_unverified", True)
            is_high_risk = flag.get("risk_level", "").lower() == "high"
            if is_unverified or is_high_risk:
                high_risk_flags.append({
                    "concern": flag.get("concern"),
                    "risk_level": flag.get("risk_level"),
                    "is_unverified": is_unverified
                })
        
    # Test forced webhook trigger
    high_risk_flags.append({"concern": "Test High Risk", "risk_level": "high", "is_unverified": False})

    if high_risk_flags:
        webhook_url = os.environ.get("N8N_WEBHOOK_URL")
        if webhook_url:
            try:
                requests.post(webhook_url, json={"contract_id": thread_id, "flags": high_risk_flags})
            except Exception as e:
                print(f"n8n webhook failed: {e}")

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
    if state.next:
        return {"status": "awaiting_review"}
    return {"status": "complete"}

@router.get("/{contract_id}/results")
async def get_contract_results(contract_id: str, tenant: TenantContext = Depends(get_current_tenant), graph: Any = Depends(get_graph)):
    config = {"configurable": {"thread_id": contract_id}}
    state = graph.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Not Found")
    if state.values.get("tenant_id") != tenant.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return {
        "jurisdiction": state.values.get("jurisdiction_result"),
        "clauses": state.values.get("extraction_result", {}).get("clauses", []),
        "risk_flags": state.values.get("risk_analysis_result", [])
    }

@router.get("/{contract_id}/review-queue")
async def get_review_queue(contract_id: str, tenant: TenantContext = Depends(get_current_tenant), graph: Any = Depends(get_graph)):
    config = {"configurable": {"thread_id": contract_id}}
    state = graph.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Not Found")
    if state.values.get("tenant_id") != tenant.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    queue = []
    if "risk_analysis_result" in state.values:
        for flag in state.values["risk_analysis_result"]:
            if flag.get("is_unverified"):
                queue.append(flag)
    return {"queue": queue}

@router.post("/{contract_id}/review")
async def submit_review(contract_id: str, payload: dict, tenant: TenantContext = Depends(get_current_tenant), graph: Any = Depends(get_graph)):
    config = {"configurable": {"thread_id": contract_id}}
    state = graph.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Not Found")
    if state.values.get("tenant_id") != tenant.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    graph.update_state(config, {"human_review_decision": payload.get("decision")}, as_node="human_review")
    return {"status": "review_submitted", "flag_id": payload.get("flag_id"), "decision": payload.get("decision")}
