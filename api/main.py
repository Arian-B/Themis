"""
api/main.py — FastAPI application factory for Themis.

Architecture:
  - Multi-tenant: every request carries a JWT with tenant_id claim.
    api/dependencies.py extracts tenant context; all downstream calls pass it through.
  - Middleware stack (applied in order):
      1. CORSMiddleware — allow frontend origin in dev; restrict in prod
      2. PIIRedactionMiddleware — Presidio pass on inbound text payloads
      3. RequestLoggingMiddleware — structured JSON logs with trace_id
      4. AuthMiddleware — JWT validation + tenant_id extraction
  - All routers are prefixed with /api/v1/ for versioning.
  - Langfuse instrumentation is injected as a LangChain callback at request scope.

Startup:
  - Verifies Qdrant, Neo4j, Ollama connectivity on startup.
  - Pulls required Ollama models if not present (dev convenience).

Usage:
  uvicorn api.main:app --reload --port 8000
"""

import logging
import os

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

# TODO (Phase 1): Import and include routers
# from api.routers import contracts, portfolio, negotiate, monitoring
# TODO (Phase 1): Add middleware stack
# TODO (Phase 1): Implement lifespan startup health checks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify service connectivity. Shutdown: flush Langfuse + clean up pools."""
    # --- Startup ---
    logger.info(
        "Themis API starting. Environment: %s",
        os.getenv("ENVIRONMENT", "development"),
    )
    # TODO (Phase 1): Check Qdrant, Neo4j, Ollama health endpoints
    # TODO (Phase 1): Pull Ollama models if missing

    yield

    # --- Shutdown ---
    # Flush pending Langfuse trace events before the process exits.
    # Without this, buffered events can be lost on SIGTERM.
    from observability.langfuse_callbacks import flush_langfuse
    flush_langfuse()
    logger.info("Langfuse events flushed. Themis API shut down.")


def create_app() -> FastAPI:
    """Application factory. Called by uvicorn and by tests (with test config)."""
    app = FastAPI(
        title="Themis Legal Intelligence API",
        description="Multi-agent contract analysis and compliance monitoring platform.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # Vite dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # TODO (Phase 1): app.include_router(contracts.router, prefix="/api/v1")
    # TODO (Phase 4): app.include_router(portfolio.router, prefix="/api/v1")
    # TODO (Phase 4): app.include_router(negotiate.router, prefix="/api/v1")
    # TODO (Phase 4): app.include_router(monitoring.router, prefix="/api/v1")

    @app.get("/health", tags=["ops"], summary="Health check")
    async def health() -> dict:
        """Liveness probe for Docker healthcheck and Kubernetes readiness probe."""
        return {"status": "ok", "version": app.version}

    return app


app = create_app()
