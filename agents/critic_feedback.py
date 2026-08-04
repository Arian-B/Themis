"""
agents/critic_feedback.py — Agent 8: Critic / Feedback Agent.

Responsibility:
  Consumes human override events from the HITL interrupt queue (populated when
  a reviewer overrides an agent's decision) and persists CorrectionRecords that
  are used to tune risk thresholds and improve the system over time.

  This agent is NOT on the hot path of contract analysis. It runs:
    a) After a human override is recorded (triggered by interrupt_before resume)
    b) In a nightly batch to aggregate corrections and update thresholds

Feedback loop mechanism:
  1. Human reviewer sees a VerifiedRiskReport and disagrees with a RiskItem
  2. HITL interrupt fires; reviewer submits HumanOverride via API
  3. Graph resumes; CriticFeedbackAgent._run() is called
  4. Agent records HumanOverride → CorrectionRecord in PostgreSQL
  5. Nightly job aggregates CorrectionRecords → updates risk scoring weights
     (stored as configuration, not model fine-tuning — simpler and auditable)

Data written (NOT to ThemisState — to persistent storage):
  - PostgreSQL table: correction_records (tenant_id, session_id, node_name,
    original_output, human_override, override_reason, timestamp)

ThemisState updates:
  - state["errors"]: cleared / archived for this session
  - state["human_override"]: set to None after processing
"""

from __future__ import annotations

from typing import Any, ClassVar

from agents.base_agent import BaseAgent
from graph.state import ThemisState
from schemas.feedback import CorrectionRecord

# TODO (Phase 3e): Implement _run():
#   1. Read state["human_override"] (HumanOverride schema)
#   2. Build CorrectionRecord from override + session context
#   3. Write to PostgreSQL (not Neo4j — relational for audit/aggregation)
#   4. Clear state["human_override"], update state["pending_human_review"] = False
#   5. Return partial state update


class CriticFeedbackAgent(BaseAgent):
    node_name: ClassVar[str] = "critic_feedback"
    output_schema: ClassVar[type[CorrectionRecord]] = CorrectionRecord

    async def _run(self, state: ThemisState) -> dict[str, Any]:
        raise NotImplementedError("Phase 3e: CriticFeedbackAgent._run() not implemented")
