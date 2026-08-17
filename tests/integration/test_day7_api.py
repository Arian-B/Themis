import os
import sys
import time
import requests
from pathlib import Path

# Add root to pythonpath
ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# We'll use the test backdoor we created: "test-token-{tenant_id}"
API_URL = "http://localhost:8000/api/v1"
HEADERS = {
    "Authorization": "Bearer test-token-tenant-123"
}

def test_full_pipeline():
    print("\n[+] Testing /contracts/upload")
    file_path = "data/raw/MSA_SaaS.txt"
    with open(file_path, "rb") as f:
        res = requests.post(f"{API_URL}/contracts/upload", headers=HEADERS, files={"file": ("MSA_SaaS.txt", f)})
    
    assert res.status_code == 200, f"Failed: {res.text}"
    cid = res.json()["contract_id"]
    print(f"Uploaded successfully. Contract ID: {cid}")
    
    print("\n[+] Polling /contracts/{contract_id}/status")
    # Wait until status is awaiting_review or complete
    status = "processing"
    while status == "processing":
        res = requests.get(f"{API_URL}/contracts/{cid}/status", headers=HEADERS)
        assert res.status_code == 200, f"Status poll failed: {res.text}"
        data = res.json()
        status = data["status"]
        print(f"Status: {status}")
        if status == "processing":
            time.sleep(5)
            
    print("\n[+] Testing /contracts/{contract_id}/results")
    res = requests.get(f"{API_URL}/contracts/{cid}/results", headers=HEADERS)
    assert res.status_code == 200, f"Results failed: {res.text}"
    flags = res.json().get('risk_flags', [])
    print(f"Results fetched! Extracted risk flags: {len(flags)}")
    
    print("\n[+] Testing Tenant Isolation")
    bad_headers = {"Authorization": "Bearer test-token-tenant-999"}
    res_b = requests.get(f"{API_URL}/contracts/{cid}/results", headers=bad_headers)
    assert res_b.status_code == 403, f"Isolation failed, got {res_b.status_code}"
    print("Tenant Isolation verified (got 403 for Tenant 999).")
    
    print("\n[+] Testing /contracts/{contract_id}/review-queue")
    res = requests.get(f"{API_URL}/contracts/{cid}/review-queue", headers=HEADERS)
    assert res.status_code == 200, f"Review queue failed: {res.text}"
    queue = res.json()
    print(f"Items in review queue: {len(queue.get('queue', []))}")
    
    if queue.get('queue'):
        print("\n[+] Testing /contracts/{contract_id}/review")
        # Find one flag
        flag = queue['queue'][0]
        flag_id = flag['clause_id']
        
        payload = {
            "flag_id": flag_id,
            "status": "rejected" # or accepted
        }
        res = requests.post(f"{API_URL}/contracts/{cid}/review", headers=HEADERS, json=payload)
        assert res.status_code == 200, f"Review failed: {res.text}"
        print(f"Review submitted for {flag_id}. Response: {res.json()}")

    print("\n[+] Testing n8n Webhook Log")
    log_file = Path("n8n_high_risk_flags.log")
    if log_file.exists():
        lines = log_file.read_text().strip().split('\n')
        print(f"n8n Webhook fired {len(lines)} times! Last payload:")
        print(lines[-1][:200] + "...")
    else:
        print("No n8n webhook log found. Maybe no high risk flags?")

if __name__ == "__main__":
    test_full_pipeline()
