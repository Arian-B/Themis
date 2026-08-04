"""
agents/atomic_verification.py — Agent 4: Atomic Verification Agent.

Responsibility:
  Receives state["risk_report"] and verifies every claim before it reaches the user.
  The core principle: no assertion is surfaced unless it can be grounded in a
  specific retrieved text chunk from the legal corpus.

Algorithm (per RiskItem in RiskReport):
  1. Decompose risk_rationale into atomic assertions
     (e.g., "This clause shifts liability" → ["liability is shifted", "no cap is present"])
  2. For each atomic assertion:
     a. Retrieve the top-1 most relevant source chunk via MCP search_corpus
     b. Ask Claude: "Does this text support this assertion? Answer YES/NO + quote."
     c. If YES: mark assertion as VERIFIED with source quote
     d. If NO:  mark assertion as UNVERIFIED; it is EXCLUDED from VerifiedRiskReport
  3. A RiskItem survives to VerifiedRiskReport only if ALL its atomic assertions are VERIFIED.
  4. Partially-verified items are downgraded in risk_level (e.g., HIGH → MEDIUM)
     and flagged with verification_partial=True.

Design rationale:
  This two-pass approach (generate then verify) is the core quality guarantee
  of Themis. It is what separates the platform from a simple "ask the LLM about
  the contract" tool. Every claim the user sees has a provenance trail.

Output: state["verified_risk_report"] = VerifiedRiskReport.model_dump()
"""

from __future__ import annotations

from typing import Any, ClassVar

from agents.base_agent import BaseAgent
from graph.state import ThemisState
from schemas.risk import VerifiedRiskReport

# TODO (Phase 3a): Implement _run():
#   1. Deserialise state["risk_report"] into RiskReport
#   2. For each RiskItem: decompose rationale into atomic assertions (Claude)
#   3. For each assertion: retrieve + verify (Claude YES/NO)
#   4. Build VerifiedRiskReport: only verified items survive
#   5. Log discarded items to state["errors"] for Critic/Feedback Agent
#   6. Return {"verified_risk_report": verified.model_dump()}


class AtomicVerificationAgent(BaseAgent):
    node_name: ClassVar[str] = "atomic_verification"
    output_schema: ClassVar[type[VerifiedRiskReport]] = VerifiedRiskReport

    async def _run(self, state: ThemisState) -> dict[str, Any]:
        raise NotImplementedError("Phase 3a: AtomicVerificationAgent._run() not implemented")
