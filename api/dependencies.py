from __future__ import annotations

import os
import requests
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer()

@dataclass
class TenantContext:
    tenant_id: str
    user_id: str

async def get_current_tenant(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> TenantContext:
    token = credentials.credentials
    # Backdoor for local testing
    if os.environ.get("ENVIRONMENT") == "development" and token.startswith("test-token-"):
        parts = token.split("-")
        return TenantContext(tenant_id=parts[3], user_id="test-user")
    url = os.environ.get("SUPABASE_URL")
    anon_key = os.environ.get("SUPABASE_ANON_KEY")
    
    if not url or not anon_key:
        raise HTTPException(status_code=500, detail="Missing Supabase config")
        
    # Validate token via Supabase Auth
    resp = requests.get(
        f"{url}/auth/v1/user",
        headers={"apikey": anon_key, "Authorization": f"Bearer {token}"}
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
        
    user_data = resp.json()
    user_id = user_data.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        
    # Get tenant_id from public.users table using service role key
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    db_resp = requests.get(
        f"{url}/rest/v1/users?id=eq.{user_id}&select=tenant_id",
        headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"}
    )
    
    if db_resp.status_code >= 400 or not db_resp.json():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not found or no tenant assigned")
        
    tenant_id = db_resp.json()[0].get("tenant_id")
    return TenantContext(tenant_id=tenant_id, user_id=user_id)

async def get_graph(request: Request):
    graph = getattr(request.app.state, "graph", None)
    if not graph:
        raise HTTPException(status_code=500, detail="Graph not initialized")
    return graph
