"""
api/middleware/auth.py — JWT authentication middleware + tenant isolation.

Responsibility:
  Validates the Bearer JWT on every request (except /health and /docs).
  Extracts tenant_id and user_id from token claims and attaches a TenantContext
  to request.state so downstream code can access it without re-decoding.

  This middleware runs BEFORE the PIIRedactionMiddleware so that unauthenticated
  requests are rejected before any content processing occurs.

Token structure (claims):
  {
    "sub":       "<user_id>",       # standard JWT subject
    "tenant_id": "<tenant_id>",     # Themis-specific claim
    "exp":       <unix_timestamp>,  # standard JWT expiry
    "iat":       <unix_timestamp>   # issued-at
  }

Excluded paths (no auth required):
  - GET  /health         — Docker / k8s health probe
  - GET  /docs           — Swagger UI (disable in production via ENVIRONMENT check)
  - GET  /openapi.json   — OpenAPI schema

Multi-tenant isolation guarantee:
  Once tenant_id is bound to request.state.tenant, all downstream operations
  (graph invocation, Qdrant queries, Neo4j queries) receive it explicitly.
  There is no global mutable state storing tenant context — each request is
  completely isolated.

TODO (Phase 1): Implement using jose.jwt.decode() + Starlette BaseHTTPMiddleware.
"""

from __future__ import annotations

# TODO (Phase 1): Implement
# from starlette.middleware.base import BaseHTTPMiddleware
# from starlette.requests import Request
# from jose import JWTError, jwt

EXCLUDED_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

# class AuthMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#         if request.url.path in EXCLUDED_PATHS:
#             return await call_next(request)
#         # decode JWT, set request.state.tenant, call_next, handle JWTError
