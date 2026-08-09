"""
graph/build.py — LangGraph StateGraph construction for Themis Day 2.

Wires the two implemented agent nodes into a linear StateGraph:
  START → jurisdiction_classifier → extraction_agent → END

This is intentionally simple for Day 2. The full topology (retry cycles,
HITL interrupts, fan-out to risk/KG agents) is added in later phases.

Usage:
    from graph.build import build_graph
    graph = build_graph()
    result = graph.invoke(initial_state)

Design notes:
  - The graph is compiled without a checkpointer for Day 2 (no persistence needed
    for the test run). In production, this is replaced with a PostgresSaver.
  - Both nodes are plain synchronous callables (not async) because LangGraph
    handles sync nodes correctly and llama3.1:8b calls are CPU-bound locally.
  - Node names match the state field names (jurisdiction_classifier writes
    jurisdiction_result, extraction_agent writes extraction_result) so LangGraph's
    automatic state merge works without custom reducers.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from agents.extraction_agent import extract_clauses
from agents.jurisdiction_classifier import classify_jurisdiction
from graph.state import ThemisState

logger = logging.getLogger(__name__)


def build_graph():
    """
    Build and compile the Day 2 Themis graph.

    Returns:
        A compiled LangGraph graph that accepts ThemisState as input.
    """
    builder = StateGraph(ThemisState)

    # ── Nodes ──────────────────────────────────────────────────────────────────
    builder.add_node("jurisdiction_classifier", classify_jurisdiction)
    builder.add_node("extraction_agent", extract_clauses)

    # ── Edges — linear for Day 2 ───────────────────────────────────────────────
    builder.add_edge(START, "jurisdiction_classifier")
    builder.add_edge("jurisdiction_classifier", "extraction_agent")
    builder.add_edge("extraction_agent", END)

    graph = builder.compile()
    logger.info("Themis Day 2 graph compiled: START → jurisdiction_classifier → extraction_agent → END")
    return graph
