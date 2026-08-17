import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.main import app
from api.dependencies import get_current_tenant, TenantContext

def test_isolation():
    # Use context manager to trigger lifespan
    with TestClient(app) as client:
        # 1. Upload as Tenant A
        app.dependency_overrides[get_current_tenant] = lambda: TenantContext(tenant_id="tenant-A", user_id="user-A")
        print("Uploading contract as Tenant A...")
        res = client.post("/api/v1/contracts/upload", files={"file": ("test.txt", b"dummy contract")})
        assert res.status_code == 200
        cid = res.json()["contract_id"]
        print(f"Contract {cid} uploaded by Tenant A.")
        
        # 2. Try to access as Tenant B
        app.dependency_overrides[get_current_tenant] = lambda: TenantContext(tenant_id="tenant-B", user_id="user-B")
        print("Attempting to read contract results as Tenant B...")
        res_b = client.get(f"/api/v1/contracts/{cid}/results")
        print(f"Tenant B Response: {res_b.status_code} - {res_b.text}")
        assert res_b.status_code == 403

if __name__ == "__main__":
    test_isolation()
