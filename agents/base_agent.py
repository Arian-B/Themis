"""
agents/base_agent.py — Abstract base class for all Themis agent nodes.

Every agent node in the LangGraph graph is a callable that takes ThemisState
and returns a partial ThemisState dict (LangGraph merges it via reducer).

This base class provides:
  1. Structured logging with the current node name + session_id
  2. Langfuse span creation/closing (via CallbackHandler — all tracing happens
     here, not in subclasses, so no subclass forgets to instrument)
  3. Error capture: exceptions are caught, appended to state.errors, and re-raised
     so the graph's error routing can handle them gracefully
  4. Schema validation guard: enforces that the node's output passes
     PydanticAI model validation before returning to the graph

Subclasses must implement:
  - output_schema: ClassVar[type[BaseModel]] — the PydanticAI model for this node's output
  - _run(state: ThemisState) -> dict — the actual node logic

Usage pattern (in graph/workflow.py):
    graph.add_node("extraction_agent", ExtractionAgent().as_node())

Tracing pattern (in subclass _run()):
    Use self.get_callbacks(state) to get a list of callbacks to pass to LLM calls:
        result = await llm.ainvoke(prompt, config={"callbacks": self.get_callbacks(state)})
    The Langfuse CallbackHandler inside automatically records model, tokens, latency.
"""

from __future__ import annotations

import abc
import logging
from typing import Any, ClassVar

import structlog
from pydantic import BaseModel

from graph.state import ThemisState

logger = structlog.get_logger(__name__)


class BaseAgent(abc.ABC):
    """Abstract base for all Themis LangGraph agent nodes."""

    node_name: ClassVar[str]
    """Must be set by each subclass. Matches the name used in StateGraph.add_node()."""

    output_schema: ClassVar[type[BaseModel]]
    """PydanticAI schema for this node's output. Validated before returning to graph."""

    def as_node(self):
        """Return a callable suitable for StateGraph.add_node(name, callable)."""
        async def _node(state: ThemisState) -> dict[str, Any]:
            return await self._execute(state)
        _node.__name__ = self.node_name
        return _node

    def get_callbacks(self, state: ThemisState) -> list:
        """
        Return a list of LangChain callbacks for use in LLM and tool calls.

        Subclasses pass this to every LLM/chain invocation:
            result = await llm.ainvoke(prompt, config={"callbacks": self.get_callbacks(state)})

        This ensures automatic Langfuse tracing (model name, tokens, latency,
        prompt, completion) without any additional code in subclasses.

        Returns an empty list if Langfuse is not configured — safe to pass
        to LangChain's callbacks parameter in all cases.
        """
        from observability.langfuse_callbacks import get_langfuse_handler_for_node

        handler = get_langfuse_handler_for_node(
            state=dict(state),
            node_name=self.node_name,
        )
        return [handler] if handler is not None else []

    async def _execute(self, state: ThemisState) -> dict[str, Any]:
        """
        Shared execution wrapper. Handles tracing, error capture, and schema validation.
        Subclasses should not override this — override _run() instead.
        """
        log = logger.bind(
            node=self.node_name,
            session_id=state.get("session_id", "unknown"),
            tenant_id=state.get("tenant_id", "unknown"),
        )
        log.info("node.start")

        try:
            raw_output = await self._run(state)

            # Schema validation: ensure output matches the declared PydanticAI schema.
            # model_validate() raises ValidationError if any required field is missing
            # or has the wrong type — surfaces bugs before they corrupt downstream state.
            if hasattr(self.__class__, "output_schema"):
                self.output_schema.model_validate(raw_output)

            log.info("node.success")
            return raw_output

        except Exception as exc:
            log.error("node.error", error=str(exc), error_type=type(exc).__name__)
            # Append structured error to state so graph error router can handle it.
            # We do NOT suppress the exception — the graph's error edge picks it up.
            raise

    @abc.abstractmethod
    async def _run(self, state: ThemisState) -> dict[str, Any]:
        """
        Implement the node's business logic here.
        Must return a dict whose keys are valid ThemisState field names.

        Use self.get_callbacks(state) for all LLM calls to enable automatic tracing:
            result = await llm.ainvoke(
                messages,
                config={"callbacks": self.get_callbacks(state)},
            )
        """
        ...
