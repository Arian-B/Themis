"""
graph/build.py — LangGraph StateGraph construction for Themis Day 5.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from agents.extraction_agent import extract_clauses
from agents.jurisdiction_classifier import classify_jurisdiction
from agents.risk_analysis_agent import analyze_risk
from agents.verification_agent import verify_risks
from agents.knowledge_graph_writer import extract_and_write_kg
from graph.state import ThemisState

logger = logging.getLogger(__name__)


def human_review_node(state: ThemisState) -> dict:
    """
    Dummy node representing human review wait state. 
    Execution pauses *before* this node due to interrupt_before.
    When resumed (via CLI or UI updating the state), it simply passes state through.
    """
    logger.info("human_review: Graph resumed after human intervention.")
    return {"pending_human_review": False}


def route_after_verification(state: ThemisState) -> str:
    """
    Conditional routing logic: 
    If there are any UNVERIFIED or HIGH risk flags, route to human review.
    Otherwise, route directly to knowledge graph writer.
    """
    ver_result = state.get("verification_result", [])
    
    requires_review = False
    for flag in ver_result:
        if not flag.get("verified", False):
            requires_review = True
            break
        if flag.get("severity", "").lower() == "high":
            requires_review = True
            break
            
    if requires_review:
        logger.info("route_after_verification: Unverified or high-risk claims found. Routing to human_review.")
        return "human_review"
    else:
        logger.info("route_after_verification: All claims verified and non-high risk. Routing to knowledge_graph_writer.")
        return "knowledge_graph_writer"


def build_graph(checkpointer=None):
    """
    Build and compile the Day 5 Themis graph.

    Args:
        checkpointer: Optional checkpointer for state persistence and interrupts.
        
    Returns:
        A compiled LangGraph graph that accepts ThemisState as input.
    """
    builder = StateGraph(ThemisState)

    # ── Nodes ──────────────────────────────────────────────────────────────────
    builder.add_node("jurisdiction_classifier", classify_jurisdiction)
    builder.add_node("extraction_agent", extract_clauses)
    builder.add_node("risk_analysis_agent", analyze_risk)
    builder.add_node("verification_agent", verify_risks)
    builder.add_node("human_review", human_review_node)
    builder.add_node("knowledge_graph_writer", extract_and_write_kg)

    # ── Edges ──────────────────────────────────────────────────────────────────
    builder.add_edge(START, "jurisdiction_classifier")
    builder.add_edge("jurisdiction_classifier", "extraction_agent")
    builder.add_edge("extraction_agent", "risk_analysis_agent")
    builder.add_edge("risk_analysis_agent", "verification_agent")
    
    # Conditional edge after verification
    builder.add_conditional_edges(
        "verification_agent",
        route_after_verification,
        {
            "human_review": "human_review",
            "knowledge_graph_writer": "knowledge_graph_writer"
        }
    )
    
    builder.add_edge("human_review", "knowledge_graph_writer")
    builder.add_edge("knowledge_graph_writer", END)

    # Compile with checkpointer and interrupt
    graph = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"]
    )
    
    logger.info("Themis Day 5 graph compiled with Human Review Gate and KG Writer")
    return graph
