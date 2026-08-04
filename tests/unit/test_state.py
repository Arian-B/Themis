"""
tests/unit/test_state.py — Unit tests for ThemisState TypedDict structure.

Verifies that:
  - ThemisState fields are correctly typed and optional
  - The add_messages reducer behaves correctly for message appending
  - State partial updates don't clobber existing fields (LangGraph merge semantics)
"""

from __future__ import annotations

import pytest
from langgraph.graph import add_messages


class TestThemisStateMerge:
    """
    LangGraph merges partial state dicts returned by agent nodes.
    These tests verify that the add_messages reducer and field optionality
    work as expected before we wire up the full graph.
    """

    def test_messages_reducer_appends(self):
        """add_messages should accumulate, not replace."""
        existing = [{"role": "assistant", "content": "first"}]
        new_msg = [{"role": "assistant", "content": "second"}]
        merged = add_messages(existing, new_msg)
        assert len(merged) == 2

    def test_messages_reducer_empty_start(self):
        existing = []
        new_msg = [{"role": "assistant", "content": "hello"}]
        merged = add_messages(existing, new_msg)
        assert len(merged) == 1

    def test_state_is_total_false(self):
        """ThemisState has total=False, so partial construction is valid."""
        from graph.state import ThemisState
        # Should not raise — all fields are optional
        partial: ThemisState = {
            "tenant_id": "acme",
            "session_id": "sess-001",
        }
        assert partial["tenant_id"] == "acme"

    def test_errors_field_accepts_list(self):
        from graph.state import ThemisState
        state: ThemisState = {
            "tenant_id": "acme",
            "session_id": "sess-002",
            "errors": [
                {"node": "extraction_agent", "error_type": "ValueError", "message": "bad pdf"}
            ],
        }
        assert len(state["errors"]) == 1
