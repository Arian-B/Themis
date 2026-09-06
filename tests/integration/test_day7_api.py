import os
import sys
import time
import requests
from pathlib import Path

# Add root to pythonpath
ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# We'll use the test backdoor we created: "test-token-{tenant_id}"
API_URL = "http://localhost:8000/api/v1"
HEADERS = {
    "Authorization": "Bearer test-token-e46cc0b7-adaa-55b9-b2e7-67ab3ebb168a"
}


def test_full_pipeline():
    # Pre-flight: confirm at least one inference provider is reachable.
    # (Ollama preferred for local extraction; cloud fallback: Groq/Kimi keys.)
    ollama_ok = False
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        ollama_ok = (r.status_code == 200)
        print("[+] Pre-flight: Ollama is running")
    except Exception as e:
        print(f"[!] Pre-flight: Ollama not reachable ({e.__class__.__name__}). Checking cloud provider keys...")

    cloud_ok = bool(
        (os.environ.get("GROQ_API_KEY") and os.environ.get("GROQ_API_KEY", "").strip() and not os.environ.get("GROQ_API_KEY").startswith("<"))
        or
        (os.environ.get("KIMI_API_KEY") and os.environ.get("KIMI_API_KEY", "").strip() and not os.environ.get("KIMI_API_KEY").startswith("<"))
    )
    if cloud_ok:
        print(f"[+] Pre-flight: cloud provider key present (GROQ_API_KEY set={bool(os.environ.get('GROQ_API_KEY'))}, KIMI_API_KEY set={bool(os.environ.get('KIMI_API_KEY'))})")

    if not (ollama_ok or cloud_ok):
        raise AssertionError(
            f"[FATAL] No inference provider available. Ollama at localhost:11434 is "
            f"unreachable, and no cloud provider API key (GROQ_API_KEY/KIMI_API_KEY) is set. "
            f"Extraction will silently return 0 clauses."
        )
    print("\n[+] Testing /contracts/upload")
    file_path = "data/raw/MSA_SaaS.txt"
    with open(file_path, "rb") as f:
        res = requests.post(f"{API_URL}/contracts/upload", headers=HEADERS, files={"file": ("MSA_SaaS.txt", f)})
    
    assert res.status_code == 200, f"Failed: {res.text}"
    cid = res.json()["contract_id"]
    print(f"Uploaded successfully. Contract ID: {cid}")
    
    print("\n[+] Polling /contracts/{contract_id}/status")
    # Wait until status is awaiting_review or complete, with a 300s timeout
    status = "processing"
    max_retries = 60
    retries = 0
    while status == "processing" and retries < max_retries:
        res = requests.get(f"{API_URL}/contracts/{cid}/status", headers=HEADERS)
        assert res.status_code == 200, f"Status poll failed: {res.text}"
        data = res.json()
        status = data["status"]
        print(f"Status: {status}")
        if status == "processing":
            time.sleep(5)
            retries += 1

    assert status != "processing", "Polling timed out after 300 seconds."

    print("\n[+] Testing /contracts/{contract_id}/results")
    res = requests.get(f"{API_URL}/contracts/{cid}/results", headers=HEADERS)
    assert res.status_code == 200, f"Results failed: {res.text}"
    flags = res.json().get('risk_flags', [])
    full_result = res.json()
    print(f"Results fetched! Extracted risk flags: {len(flags)}")
    print(f"Full result:\n  clauses: {len(full_result.get('clauses', []))}")
    for flag in flags:
        concern_safe = str(flag.get('concern', ''))[:100].encode('ascii', 'ignore').decode('ascii')
        print(f"  flag [{flag.get('risk_level')}] grounded={flag.get('grounded')} concern={concern_safe}")

    assert len(flags) > 0, (
        f"Expected >0 risk flags for MSA_SaaS.txt (known high-risk contract), got 0. "
        f"Clauses extracted: {len(full_result.get('clauses', []))}. "
        f"This is a silent failure — check that Ollama is running and extraction succeeded."
    )
    print(f"[PASS] {len(flags)} risk flags returned — pipeline produced real output.")
    
    print("\n[+] Testing Tenant Isolation")
    bad_headers = {"Authorization": "Bearer test-token-tenant-00000000-0000-0000-0000-000000000999"}
    res_b = requests.get(f"{API_URL}/contracts/{cid}/results", headers=bad_headers)
    assert res_b.status_code == 403, f"Isolation failed, got {res_b.status_code}"
    print("Tenant Isolation verified (got 403 for Tenant 999).")
    
    print("\n[+] Testing /contracts/{contract_id}/review-queue")
    res = requests.get(f"{API_URL}/contracts/{cid}/review-queue", headers=HEADERS)
    assert res.status_code == 200, f"Review queue failed: {res.text}"
    queue = res.json().get('queue', [])
    print(f"Items in review queue: {len(queue)}")
    for item in queue:
        concern_safe = str(item.get('concern', ''))[:100].encode('ascii', 'ignore').decode('ascii')
        print(f"  queue item [{item.get('risk_level')}] grounded={item.get('grounded')} clause={item.get('clause_id', '')[:8]}... concern={concern_safe}")

    verification = {flag.get("clause_id"): flag for flag in flags}
    assert queue, "Expected at least one high-risk or ungrounded review item."
    for item in queue:
        source_flag = verification.get(item.get("clause_id"), item)
        assert (
            source_flag.get("risk_level", "").lower() == "high"
            or source_flag.get("grounded") is False
        ), f"Queue item violates review rule: {item}"
    print("[PASS] Every review item is high risk or ungrounded.")

    print("\n[+] Testing /contracts/{contract_id}/review (submit one decision)")
    flag_id = queue[0]['clause_id']
    res = requests.post(f"{API_URL}/contracts/{cid}/review", headers=HEADERS,
                        json={"flag_id": flag_id, "decision": "accepted"})
    assert res.status_code == 200, f"Review submission failed: {res.text}"
    print(f"Review submitted for clause {flag_id[:8]}... Response: {res.json()}")

    print("\n[+] All core API tests passed — n8n webhook removed from scope.")


if __name__ == "__main__":
    test_full_pipeline()
