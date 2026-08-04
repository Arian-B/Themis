"""
observability/langfuse_callbacks.py — Langfuse tracing integration for Themis.

This module wires the Langfuse CallbackHandler into every LangGraph agent node
via the BaseAgent._execute() wrapper. All LLM calls, tool calls, and retrievals
are captured automatically through LangChain's callback system.

## What gets traced automatically (via CallbackHandler):
  - Every LLM call: model name, token usage (input/output), latency, prompt, completion
  - Every tool call: tool name, inputs, outputs
  - Every retrieval: query, retrieved documents, source chunks
  - Errors: exception type, message, which node failed

## What we set explicitly:
  - trace_id    → session_id from ThemisState (ties all nodes in one analysis together)
  - trace_name  → descriptive name like "contract-analysis" (not "trace-1")
  - user_id     → user_id from TenantContext (for per-user filtering)
  - session_id  → session_id (for session grouping in Langfuse UI)
  - tags        → ["tenant:<id>", "jurisdiction:<id>", "node:<name>"]
  - metadata    → {tenant_id, contract_id, jurisdiction}

## PII safety:
  Presidio redaction runs in api/middleware/pii_redaction.py BEFORE any text
  reaches this module. Langfuse receives only redacted text — no raw PII enters
  the self-hosted trace store.

## Why self-hosted Langfuse?
  Contract content is legally sensitive. LANGFUSE_HOST points to the local Docker
  container (http://langfuse:3000 inside compose, http://localhost:3000 from host).
  No trace data leaves the local network.

## SDK: langfuse>=3.0 (v4 SDK)
  The v4 SDK uses environment variables for auto-configuration:
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
  CallbackHandler picks these up automatically — no explicit client needed.
  Docs: https://langfuse.com/docs/integrations/langchain

## Usage in agents/base_agent.py:
    from observability.langfuse_callbacks import get_langfuse_handler, flush_langfuse
    handler = get_langfuse_handler(
        trace_id=state["session_id"],
        user_id=state["user_id"],
        tenant_id=state["tenant_id"],
        contract_id=state.get("contract_id"),
        jurisdiction=state.get("jurisdiction"),
        node_name=self.node_name,
    )
    result = await llm.ainvoke(prompt, config={"callbacks": [handler]})
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)


def get_langfuse_handler(
    trace_id: str,
    user_id: str,
    tenant_id: str,
    node_name: str,
    contract_id: str | None = None,
    jurisdiction: str | None = None,
) -> "CallbackHandler":
    """
    Return a per-invocation Langfuse CallbackHandler.

    Each call creates a new handler scoped to a single agent-node execution.
    The trace_id ties all node executions within one contract analysis together
    in the Langfuse UI (they appear as a single trace with nested spans).

    Args:
        trace_id:    The session_id from ThemisState — groups all nodes in one analysis.
        user_id:     The user who uploaded the contract (for per-user dashboard filtering).
        tenant_id:   The tenant organisation (for multi-tenant dashboard segmentation).
        node_name:   The LangGraph node name (e.g. "risk_analysis_agent").
        contract_id: UUID of the contract being analysed (optional, added to metadata).
        jurisdiction: Detected jurisdiction code (e.g. "us_generic", "uk").

    Returns:
        A configured langfuse.callback.CallbackHandler instance.

    Raises:
        RuntimeError: If LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY are not set.
    """
    from langfuse.callback import CallbackHandler  # type: ignore[import]

    _require_langfuse_env()

    tags: list[str] = [f"node:{node_name}", f"tenant:{tenant_id}"]
    if jurisdiction:
        tags.append(f"jurisdiction:{jurisdiction}")

    metadata: dict[str, str | None] = {
        "tenant_id": tenant_id,
        "node_name": node_name,
        "contract_id": contract_id,
        "jurisdiction": jurisdiction,
    }

    handler = CallbackHandler(
        # Credentials and host are picked up from env vars automatically
        # (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST)
        trace_id=trace_id,
        session_id=trace_id,    # session_id = trace_id: one session per analysis
        user_id=user_id,
        trace_name="contract-analysis",     # Descriptive, not "trace-1"
        tags=tags,
        metadata=metadata,
    )

    return handler


def get_langfuse_handler_for_node(
    state: dict,
    node_name: str,
) -> "CallbackHandler | None":
    """
    Convenience wrapper that extracts context from ThemisState dict.
    Returns None (no tracing) if Langfuse env vars are not configured,
    so the system degrades gracefully in environments without Langfuse.

    Args:
        state:     ThemisState dict (as received in a LangGraph node callable).
        node_name: The LangGraph node name.

    Returns:
        A CallbackHandler, or None if Langfuse is not configured.
    """
    if not _is_langfuse_configured():
        logger.debug("Langfuse not configured — skipping tracing for node %s", node_name)
        return None

    try:
        return get_langfuse_handler(
            trace_id=state["session_id"],
            user_id=state.get("user_id", "unknown"),
            tenant_id=state.get("tenant_id", "unknown"),
            node_name=node_name,
            contract_id=state.get("contract_id"),
            jurisdiction=state.get("jurisdiction"),
        )
    except Exception as exc:
        # Never let tracing errors break the main pipeline
        logger.warning("Failed to create Langfuse handler: %s", exc)
        return None


def flush_langfuse() -> None:
    """
    Flush all pending Langfuse events to the server.

    Call this:
      - In the FastAPI lifespan shutdown handler (api/main.py)
      - In test teardown after each test that exercises LLM calls

    Without flushing, the SDK buffers events and some may be lost on abrupt exit.
    """
    try:
        from langfuse import Langfuse  # type: ignore[import]

        _get_langfuse_client().flush()
        logger.debug("Langfuse events flushed successfully")
    except Exception as exc:
        logger.warning("Langfuse flush failed (non-fatal): %s", exc)


@lru_cache(maxsize=1)
def _get_langfuse_client() -> "Langfuse":
    """
    Return a singleton Langfuse client for operations that need the client
    directly (e.g. scoring, flush). Uses env vars for configuration.
    """
    from langfuse import Langfuse  # type: ignore[import]

    return Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.getenv("LANGFUSE_HOST", "http://langfuse:3000"),
    )


def _require_langfuse_env() -> None:
    """Raise RuntimeError if required Langfuse env vars are missing."""
    missing = [
        key for key in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
        if not os.getenv(key)
    ]
    if missing:
        raise RuntimeError(
            f"Langfuse env vars not set: {missing}. "
            "Copy .env.example to .env and fill LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY. "
            "See README.md → Getting Started for setup steps."
        )


def _is_langfuse_configured() -> bool:
    """Return True if both required Langfuse env vars are present and non-empty."""
    return bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )
