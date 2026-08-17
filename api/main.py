import logging
import os
import sqlite3

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import contracts
from graph.build import build_graph
from langgraph.checkpoint.sqlite import SqliteSaver

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Themis API starting. Environment: %s", os.getenv("ENVIRONMENT", "development"))
    
    # Initialize LangGraph Checkpointer
    db_path = ".langgraph.db"
    conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    
    app.state.graph = build_graph(checkpointer=checkpointer)
    app.state.conn = conn

    yield

    from observability.langfuse_callbacks import flush_langfuse
    flush_langfuse()
    app.state.conn.close()
    logger.info("Langfuse events flushed. Themis API shut down.")

def create_app() -> FastAPI:
    app = FastAPI(
        title="Themis Legal Intelligence API",
        description="Multi-agent contract analysis and compliance monitoring platform.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(contracts.router, prefix="/api/v1")

    @app.get("/health", tags=["ops"], summary="Health check")
    async def health() -> dict:
        return {"status": "ok", "version": app.version}

    return app

app = create_app()
