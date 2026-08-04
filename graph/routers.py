"""
graph/routers.py — Conditional edge functions for the Themis LangGraph workflow.

LangGraph routes between nodes by calling these functions with the current
ThemisState and returning the name of the next node (or END). Keeping all
routing logic here (rather than inside agent nodes) keeps agents pure
data-transformers and makes the graph topology readable in one place.

Functions to implement:
  - route_after_jurisdiction(state) → str
      Returns "extraction_agent" always (could add "unsupported_jurisdiction" path)

  - route_after_extraction(state) → str
      Returns "risk_analysis_agent" if clauses found, else "END" with error

  - route_after_risk_analysis(state) → str
      Returns "atomic_verification" if risk_report present, else "error_handler"

  - route_after_verification(state) → str
      Returns "kg_writer" | "negotiation_simulation" | "END"
      based on verified_risk_report severity + presence of human_override

  - route_after_human_review(state) → str
      Returns next node based on human_override.decision field

  - route_monitoring_alert(state) → str
      Used in the background monitoring subgraph
"""

from __future__ import annotations

from graph.state import ThemisState

# TODO (Phase 1): Implement route_after_jurisdiction, route_after_extraction,
# route_after_risk_analysis. Add more routes in later phases.


def route_after_jurisdiction(state: ThemisState) -> str:
    """Route after jurisdiction classification. Stub — always goes to extraction."""
    raise NotImplementedError("Phase 1: route_after_jurisdiction not implemented")


def route_after_extraction(state: ThemisState) -> str:
    """Route after clause extraction. Goes to risk analysis or error terminal."""
    raise NotImplementedError("Phase 1: route_after_extraction not implemented")


def route_after_risk_analysis(state: ThemisState) -> str:
    """Route after risk analysis. Phase 1: goes to END; Phase 3+: atomic_verification."""
    raise NotImplementedError("Phase 1: route_after_risk_analysis not implemented")


def route_after_human_review(state: ThemisState) -> str:
    """Route based on human override decision after HITL interrupt."""
    raise NotImplementedError("Phase 3: route_after_human_review not implemented")
