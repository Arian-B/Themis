"""
agents/base_agent.py — Abstract base class for all Themis agent nodes.

Every agent node in the LangGraph graph is a callable that takes ThemisState
and returns a partial ThemisState dict (LangGraph merges it via reducer).

This base class provides:
  1. Structured logging with the current node name + session_id
  2. Langfuse span creation/closing (all tracing happens here, not in subclasses)
  3. Error capture: exceptions are caught, appended to state.errors, and re-raised
     so the graph's error routing can handle them gracefully
  4. Schema validation guard: enforces that the node's output passes
     PydanticAI model validation before returning to the graph

Subclasses must implement:
  - output_schema: ClassVar[type[BaseModel]] — the PydanticAI model for this node's output
  - _run(state: ThemisState) -> dict — the actual node logic

Usage pattern (in graph/workflow.py):
    graph.add_node("extraction_agent", ExtractionAgent().as_node())
"""

from __future__ import annotations

import abc
import logging
from typing import Any, ClassVar

from pydantic import BaseModel

from graph.state import ThemisState

logger = logging.getLogger(__name__)


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

    async def _execute(self, state: ThemisState) -> dict[str, Any]:
        """
        Shared execution wrapper. Handles tracing, error capture, and schema validation.
        Subclasses should not override this — override _run() instead.
        """
        # TODO (Phase 1): Open Langfuse span here using session_id from state
        # TODO (Phase 1): Set state["current_node"] = self.node_name
        try:
            raw_output = await self._run(state)
            # TODO (Phase 1): Validate raw_output against self.output_schema
            # TODO (Phase 1): Close Langfuse span with success status
            return raw_output
        except Exception as exc:
            # TODO (Phase 1): Close Langfuse span with error status
            # TODO (Phase 1): Append to state["errors"]
            logger.exception("Agent %s failed: %s", self.node_name, exc)
            raise

    @abc.abstractmethod
    async def _run(self, state: ThemisState) -> dict[str, Any]:
        """
        Implement the node's business logic here.
        Must return a dict whose keys are valid ThemisState field names.
        """
        ...
