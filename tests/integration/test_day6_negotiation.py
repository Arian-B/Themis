"""
tests/integration/test_day6_negotiation.py — Integration test for Day 6 (Negotiation Simulation)
"""

import os
import sys
import uuid
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from agents.negotiation_simulation import run_negotiation_node

def test_negotiation_simulation():
    # Construct a mock state representing an accepted human override for an auto-renewal flag.
    # The Day 5 audit_log flag_index 14 corresponds to auto-renewal.
    
    mock_state = {
        "human_override": {
            "overrides": [
                {"flag_index": 14, "status": "accepted"}
            ]
        },
        "risk_analysis_result": [
            {} for _ in range(14)
        ] + [
            {
                "clause_id": "c54215b2-38ef-4171-be17-f542db740f90",
                "concern": "The automatic renewal clause may lead to unintended long-term commitments for one or both parties.",
                "risk_level": "medium"
            }
        ],
        "extraction_result": {
            "clauses": [
                {
                    "clause_id": "c54215b2-38ef-4171-be17-f542db740f90",
                    "text": "8.1 Term. This Agreement commences on the Effective Date and continues for the Initial Term. Following the Initial Term, this Agreement will automatically renew for successive one-year terms unless either party provides written notice of non-renewal at least 30 days prior to the end of the then-current term."
                }
            ]
        }
    }
    
    import logging; logging.basicConfig(level=logging.INFO); print("Running negotiation node...")
    result = run_negotiation_node(mock_state)
    
    assert "negotiation_transcript" in result, "negotiation_transcript missing from result"
    transcript = result["negotiation_transcript"]
    
    print("\n--- Negotiation Transcript ---")
    print(json.dumps(transcript, indent=2))
    
    assert len(transcript["turns"]) > 1, f"Expected multiple turns, got {len(transcript['turns'])}"
    assert transcript["outcome"] in ["agreement_reached", "impasse", "max_turns_reached"]
    
if __name__ == "__main__":
    test_negotiation_simulation()
    print("\nTest passed!")
