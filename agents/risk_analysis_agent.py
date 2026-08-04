"""
agents/risk_analysis_agent.py — Agent 3: Risk Analysis Agent.

Responsibility:
  Receives state["clause_bundle"] and state["jurisdiction_result"]. For each
  extracted clause, retrieves relevant reference text from the legal corpus
  (via the MCP retrieval server), then calls Claude (Anthropic API) to assess
  risk level, identify non-standard language, and produce a structured RiskReport.

  This agent uses the strongest hosted model because risk reasoning requires:
    - Multi-step chain-of-thought across legal concepts
    - Faithfulness to retrieved source text (not hallucination)
    - Calibrated confidence scores

Model strategy:
  - Retrieval: calls tools/mcp/retrieval_server.py via MCP protocol
    (search_corpus tool with jurisdiction-filtered Qdrant collection)
  - Reasoning: Claude claude-3-5-sonnet-20241022 (or latest) via Anthropic API
  - Structured output: PydanticAI enforces RiskReport schema; Claude is
    prompted with the schema JSON and instructed to produce matching output

Risk dimensions assessed per clause:
  - risk_level: RiskLevel enum (LOW | MEDIUM | HIGH | CRITICAL)
  - risk_rationale: str — specific legal reasoning
  - non_standard_language: list[str] — exact phrases flagged
  - suggested_redline: Optional[str] — recommended replacement language
  - retrieved_sources: list[str] — source chunk IDs from Qdrant (for citation)
  - confidence: float — 0.0–1.0, how confident the model is in this assessment

Output: state["risk_report"] = RiskReport.model_dump()

Note: This output is NOT shown to the user directly. It flows into
atomic_verification_agent.py (Agent 4) which verifies each claim before display.
"""

from __future__ import annotations

from typing import Any, ClassVar

from agents.base_agent import BaseAgent
from graph.state import ThemisState
from schemas.risk import RiskReport

# TODO (Phase 1): Implement _run() with Claude + RAG:
#   1. Deserialise state["clause_bundle"] into ClauseBundle
#   2. For each clause: call MCP retrieval_server search_corpus() to get top-k chunks
#   3. Build a structured prompt: clause text + retrieved chunks + risk rubric
#   4. Call Claude with structured output mode (RiskReport schema)
#   5. Aggregate per-clause RiskItems into a single RiskReport
#   6. Return {"risk_report": risk_report.model_dump()}
#
# TODO (Phase 2): Replace direct MCP call with LangChain tool-calling agent
# so the model can decide how many retrieval calls to make per clause.


class RiskAnalysisAgent(BaseAgent):
    node_name: ClassVar[str] = "risk_analysis_agent"
    output_schema: ClassVar[type[RiskReport]] = RiskReport

    async def _run(self, state: ThemisState) -> dict[str, Any]:
        raise NotImplementedError("Phase 1: RiskAnalysisAgent._run() not implemented")
