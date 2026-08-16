"""
scripts/resume_review.py — CLI tool to review and resume paused Themis analysis runs.
"""

import os
import sys
from pathlib import Path
import sqlite3
import requests
import uuid
import datetime

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from langgraph.checkpoint.sqlite import SqliteSaver
from graph.build import build_graph

def log_audit_event(tenant_id: str, action: str, resource_type: str, resource_id: str, details: dict):
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Missing Supabase credentials, skipping audit log.")
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
        resp = requests.post(endpoint, headers=headers, json=payload)
        if resp.status_code >= 400:
            print(f"Failed to write to audit_log: {resp.text}")
    except Exception as e:
        print(f"Error calling Supabase: {e}")

def main():
    db_path = ROOT / ".langgraph.db"
    with sqlite3.connect(db_path, check_same_thread=False, isolation_level=None) as conn:
        checkpointer = SqliteSaver(conn)
        checkpointer.setup()
        graph = build_graph(checkpointer=checkpointer)
        
        # We can query the sqlite DB directly to find thread_ids.
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT thread_id FROM checkpoints")
        threads = cursor.fetchall()
        
        if not threads:
            print("No checkpoints found in database.")
            return
            
        print("Found threads:")
        paused_threads = []
        for (tid,) in threads:
            config = {"configurable": {"thread_id": tid}}
            state = graph.get_state(config)
            
            if state.next and "human_review" in state.next:
                paused_threads.append(tid)
                
        if not paused_threads:
            print("No threads currently paused for human review.")
            return
            
        print(f"Found {len(paused_threads)} thread(s) awaiting review.")
        
        for tid in paused_threads:
            print(f"\n--- Reviewing Thread: {tid} ---")
            config = {"configurable": {"thread_id": tid}}
            state = graph.get_state(config)
            vals = state.values
            
            tenant_id = vals.get("tenant_id", str(uuid.uuid4()))
            try:
                uuid.UUID(tenant_id)
            except ValueError:
                tenant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, tenant_id))
            ver_result = vals.get("verification_result", [])
            risk_flags = vals.get("risk_analysis_result", [])
            
            overrides = []
            
            for i, flag in enumerate(risk_flags):
                flag_id = flag.get("clause_id", "") + "_risk"
                
                # Check if all atomic claims for this flag are grounded
                flag_claims = [vr for vr in ver_result if vr.get("source_risk_flag_id") == flag_id]
                is_unverified = any(not vr.get("grounded", False) for vr in flag_claims)
                # If no claims were generated, consider it unverified
                if not flag_claims:
                    is_unverified = True
                    
                is_high_risk = flag.get("risk_level", "").lower() == "high"
                
                if is_unverified or is_high_risk:
                    print(f"\nRisk Flag {i+1}:")
                    print(f"  Concern: {flag.get('concern')}")
                    print(f"  Severity: {flag.get('risk_level')}")
                    print(f"  Verified: {not is_unverified}")
                    
                    choice = ""
                    while choice not in ['a', 'r']:
                        choice = input("Approve (a) or Reject (r)? ").strip().lower()
                        
                    status = "accepted" if choice == 'a' else "rejected"
                    overrides.append({"flag_index": i, "status": status})
                    
                    # Log to Supabase
                    log_audit_event(
                        tenant_id=tenant_id,
                        action="flag.overridden",
                        resource_type="flag",
                        resource_id=str(uuid.uuid4()), # Would be real flag_id if generated
                        details={"human_override": status, "flag_index": i, "concern": flag.get('concern')}
                    )
                    
            print("\nResuming graph execution...")
            # We update the state to indicate human review is complete
            graph.update_state(config, {"human_override": {"overrides": overrides}, "pending_human_review": False})
                
        # Resume the graph
        print(f"Resuming graph for thread {tid}...")
        for event in graph.stream(None, config, stream_mode="values"):
            pass
            
        print("Graph execution completed.")
        conn.commit()

if __name__ == "__main__":
    main()
