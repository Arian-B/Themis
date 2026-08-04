"""
observability/langfuse_callbacks.py — Langfuse tracing integration.

Provides a LangChain callback handler that sends traces, spans, and events
to a self-hosted Langfuse instance for every agent node execution.

Every LangGraph node call produces:
  - A Langfuse Trace (keyed by session_id)
  - A Span per agent node (start/end times, input/output)
  - Events for: LLM calls, tool calls, retrieval results, errors
  - Scores: model confidence, retrieved chunk count, verification pass rate

Usage (in agents/base_agent.py):
    from observability.langfuse_callbacks import get_langfuse_handler
    handler = get_langfuse_handler(session_id=state["session_id"])
    llm_with_tracing = llm.with_config(callbacks=[handler])

Environment variables required:
  LANGFUSE_PUBLIC_KEY   — from Langfuse project settings
  LANGFUSE_SECRET_KEY   — from Langfuse project settings
  LANGFUSE_HOST         — self-hosted: http://langfuse:3000 (docker-compose)

Why self-hosted Langfuse?
  Contract content is PII-sensitive. Sending traces to Langfuse Cloud would
  require trusting a third party with potentially redacted-but-still-sensitive
  legal text. Self-hosting keeps all trace data within the local Docker network.
"""

from __future__ import annotations

# TODO (Phase 5): Implement using:
#   from langfuse.callback import CallbackHandler
#
#   def get_langfuse_handler(session_id: str) -> CallbackHandler:
#       return CallbackHandler(
#           public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
#           secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
#           host=os.getenv("LANGFUSE_HOST", "http://langfuse:3000"),
#           trace_id=session_id,
#       )

raise NotImplementedError("Phase 5: langfuse_callbacks.py not yet implemented")
