"""
api/dependencies.py — FastAPI dependency injection for Themis.

All shared request-scoped dependencies live here. FastAPI's Depends() system
injects these into route handlers, keeping routers thin and testable.

Key dependencies:
  - get_current_tenant()  Extract + validate JWT, return TenantContext
  - get_graph()           Return the compiled LangGraph instance (singleton)
  - get_vector_store()    Return tenant-scoped Qdrant store
  - get_graph_store()     Return Neo4j graph store instance
  - get_langfuse_handler() Return a per-request Langfuse tracing handler

TenantContext:
  A lightweight dataclass that carries tenant_id and user_id through the
  request lifecycle. Every downstream call (graph invocation, DB query) receives
  this object to enforce isolation — it is never stored globally.

Usage in routers:
    from api.dependencies import get_current_tenant, TenantContext
    @router.post("/analyze")
    async def analyze(tenant: TenantContext = Depends(get_current_tenant)):
        ...

Testing:
    Override dependencies in tests via app.dependency_overrides:
    app.dependency_overrides[get_current_tenant] = lambda: TenantContext(
        tenant_id="test-tenant", user_id="test-user"
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer()


@dataclass
class TenantContext:
    """Immutable per-request tenant identity. Propagated to all downstream calls."""
    tenant_id: str
    user_id: str


async def get_current_tenant(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> TenantContext:
    """
    Validate JWT Bearer token and extract tenant_id + user_id claims.

    Raises HTTP 401 if token is missing, expired, or invalid.
    Raises HTTP 403 if tenant_id claim is absent (misconfigured token).

    TODO (Phase 1): Implement JWT decode using python-jose:
        from jose import JWTError, jwt
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        tenant_id = payload.get("tenant_id")
        user_id = payload.get("sub")
    """
    raise NotImplementedError("Phase 1: JWT validation not yet implemented")


async def get_graph():
    """
    Return the singleton compiled LangGraph instance.
    Initialised once at startup in api/main.py lifespan; accessed here via app state.

    TODO (Phase 1): Implement using app.state.graph set in lifespan context.
    """
    raise NotImplementedError("Phase 1: get_graph() not yet implemented")
