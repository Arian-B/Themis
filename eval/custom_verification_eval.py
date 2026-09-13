"""
eval/custom_verification_eval.py — Custom Verification Agent Evaluation.

Evaluates the verification agent's grounded=True/False decisions against
hand-labeled ground truth from real contract analysis runs.

This replaces the Ragas evaluation which hit a Groq API incompatibility
(n>1 sampling rejected by Groq API, documented in eval/README.md).
This custom evaluation directly measures the verification agent's
precision/recall against hand-labeled ground truth — arguably more
targeted for this project's specific claim that verification catches
unsupported claims than Ragas's generic faithfulness score.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
load_dotenv()

from graph.build import build_graph
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

# ── Ground Truth Labels (Hand-Curated from Real Contract Runs) ─────────────────
# Each entry: claim_id, claim_text, ground_truth (True=correctly grounded, False=ungrounded)
# Labels assigned by developer based on manual review of contract text and sources.

GROUND_TRUTH: List[Dict[str, Any]] = [
    # Thread 32901e38 - SaaS MSA contract
    {
        "claim_id": "2cc49526-f138-4d48-9865-733564c34bf5",
        "claim_text": "The clause provides for automatic renewal of the agreement for ten-year periods.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "c1bea824-8128-4521-8006-a6af7d3ae455",
        "claim_text": "The clause does not grant the customer any right to terminate the agreement.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "a332f087-c4ce-4fec-be37-265de9277966",
        "claim_text": "The renewal periods continue indefinitely unless the clause is otherwise amended.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "04906785-953a-45cf-bae2-c630d85a8a7c",
        "claim_text": "The clause allows the provider to change pricing and terms at any time without notice.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "7f17b66b-f24f-4b61-9ad2-11fa8ee8838d",
        "claim_text": "The clause waives the customer's right to bring a class action.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "2e86b0d7-b352-4e73-8aa9-1ff53f07c554",
        "claim_text": "The clause waives the customer's right to a jury trial.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "ee8ba691-6012-4a45-916d-cf45d7edbc2b",
        "claim_text": "The clause does not specify a liability cap.",
        "ground_truth": False,  # Actually the contract does have a cap (just no amount specified)
        "source": "none"
    },

    # Thread 713fa380 - SaaS MSA contract
    {
        "claim_id": "97233ce9-a2af-49d7-8e2d-bf3a0a6b73dc",
        "claim_text": "The clause provides for automatic renewal of the agreement for successive ten-year terms.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "3d8decb2-4ff7-4d0a-ab58-f147b7683ee7",
        "claim_text": "The clause does not grant the customer any right to terminate the agreement.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "38b7fe3f-46b3-436d-8bcf-7489d8add10e",
        "claim_text": "The clause requires no notice from either party prior to each renewal.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "56d73e1b-b888-41e1-9840-00b13886e45e",
        "claim_text": "The provider may modify pricing and other terms at any time without prior notice.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "cfdb1a91-6f7d-49a6-b276-fb32f338cdac",
        "claim_text": "The customer waives the right to bring class actions.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "9c0a5bd9-9ef5-42ce-aaab-28cf2e5cedba",
        "claim_text": "The customer waives the right to a jury trial.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "b1d2a094-3247-48b5-8b1f-ff705445758a",
        "claim_text": "The clause does not specify a liability cap.",
        "ground_truth": False,  # Actually there IS a liability cap (just amount unspecified)
        "source": "none"
    },

    # Thread 0a7f2360 - SaaS MSA contract
    {
        "claim_id": "42bfead8-9330-4f84-94c4-a7882c3a7eeb",
        "claim_text": "The clause provides for automatic renewal of ten-year terms.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "c4a6a8cc-b2fd-4dd5-8cd5-ac7ceea8615b",
        "claim_text": "The clause allows the renewal to continue indefinitely.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "9db718a5-7695-43aa-8e41-c56877114980",
        "claim_text": "The clause does not give the customer any right to terminate the agreement.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "fdf3527a-7d63-4f3b-adb6-aea06332201c",
        "claim_text": "The clause does not require the customer to give notice to avoid renewal.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "d65f0f49-1ba2-43d8-a35c-b50fdd3cdaed",
        "claim_text": "The clause allows the Provider to change price and terms without notice.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "875ac59d-411e-4261-863f-728c0caece1e",
        "claim_text": "The clause requires the Customer to waive class-action rights.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "0c82589f-0225-41f6-b7bd-c5b993307497",
        "claim_text": "The clause requires the Customer to waive jury trial rights.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "6d13c6f6-ca2c-4f74-950d-83f5340eb7be",
        "claim_text": "The clause includes a liability cap but does not specify an amount.",
        "ground_truth": True,
        "source": "contract_text"
    },

    # Thread 0e744fee - NDA contract (has some false claims)
    {
        "claim_id": "edb26daf-c005-4150-919f-8a44183929ab",
        "claim_text": "The agreement provides for automatic renewal of the term.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "2d755f46-69cd-4fcc-ac55-61607bdcb9cf",
        "claim_text": "The clause imposes unlimited liability on the receiving party.",
        "ground_truth": False,  # The NDA has a liability cap
        "source": "contract_text"
    },

    # Thread 6b4c5114 - Software License Agreement
    {
        "claim_id": "78a54cf5-51a6-4ccb-982c-bfc99dd616f7",
        "claim_text": "The license grants perpetual rights to use the software.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "979b2a52-342f-4a2e-a499-23bfbb7e52de",
        "claim_text": "The license prohibits the licensee from sublicensing the software.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "84787711-6c5e-456c-a1b6-100568992af8",
        "claim_text": "The licensee may reverse engineer the software for any purpose.",
        "ground_truth": False,  # License prohibits reverse engineering
        "source": "contract_text"
    },
    {
        "claim_id": "636834fd-ede0-4c6f-8572-e21ad9a33a93",
        "claim_text": "The license grants source code access to the licensee.",
        "ground_truth": False,  # SaaS license - no source code access
        "source": "contract_text"
    },

    # Thread 58cd35e0 - Another SaaS contract
    {
        "claim_id": "d1b4be22-6bc4-4b01-ab1b-9d20b98a8c9c",
        "claim_text": "The agreement automatically renews for successive terms.",
        "ground_truth": True,
        "source": "contract_text"
    },
    {
        "claim_id": "5b952bca-30dc-4567-b8c5-b2f098152b0e",
        "claim_text": "The customer may terminate the agreement at any time without cause.",
        "ground_truth": False,  # No termination for convenience
        "source": "contract_text"
    },
]


def load_verification_results() -> Dict[str, Dict[str, Any]]:
    """Load verification results from the most recent pipeline runs."""
    from graph.build import build_graph
    from langgraph.checkpoint.sqlite import SqliteSaver
    import sqlite3

    conn = sqlite3.connect(r"D:\Coding\themis\.langgraph.db", check_same_thread=False, isolation_level=None)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    graph = build_graph(checkpointer=checkpointer)

    cursor = sqlite3.connect(r"D:\Coding\themis\.langgraph.db", check_same_thread=False, isolation_level=None).cursor()
    cursor.execute("SELECT thread_id FROM checkpoints GROUP BY thread_id ORDER BY ROWID DESC LIMIT 20")
    threads = cursor.fetchall()

    results = {}
    for t in threads:
        tid = t[0]
        state = graph.get_state({"configurable": {"thread_id": t[0]}})
        if state.values and "verification_result" in state.values:
            ver = state.values.get("verification_result", [])
            for v in ver:
                claim_id = v.get("claim_id", "")
                if claim_id:
                    results[claim_id] = {
                        "grounded": v.get("grounded"),
                        "score": v.get("raw_cosine_score", 0),
                        "claim_text": v.get("claim_text", ""),
                        "grounding_source": v.get("grounding_source", ""),
                    }
    return results


def evaluate_verification_accuracy() -> Dict[str, Any]:
    """Compare verification agent decisions against ground truth."""
    verification_results = load_verification_results()

    # Match ground truth to verification results
    tp = fp = tn = fn = 0
    total = 0
    claim_results = []
    cosine_scores_correct = []
    cosine_scores_incorrect = []

    for gt in GROUND_TRUTH:
        claim_id = gt["claim_id"]
        ground_truth = gt["ground_truth"]
        claim_text = gt["claim_text"]

        if claim_id not in verification_results:
            print(f"WARNING: No verification result for claim {claim_id}")
            continue

        result = verification_results[claim_id]
        predicted_grounded = result.get("grounded", False)
        score = result.get("score", 0)
        claim_text = result.get("claim_text", "")
        source = result.get("grounding_source", "")

        # Compare prediction with ground truth
        if predicted_grounded and ground_truth:
            tp += 1
            cosine_scores_correct.append(result.get("score", 0))
        elif predicted_grounded and not ground_truth:
            fp += 1
            cosine_scores_incorrect.append(result.get("score", 0))
        elif not predicted_grounded and not ground_truth:
            tn += 1
            cosine_scores_correct.append(result.get("score", 0))
        else:  # not predicted_grounded and ground_truth
            fn += 1
            cosine_scores_incorrect.append(result.get("score", 0))

        total += 1
        claim_results.append({
            "claim_id": claim_id,
            "claim_text": gt["claim_text"][:120],
            "ground_truth": ground_truth,
            "predicted_grounded": predicted_grounded,
            "correct": predicted_grounded == ground_truth,
            "cosine_score": result.get("score", 0),
            "grounding_source": result.get("grounding_source", "")
        })

    # Compute metrics
    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Cosine score correlation
    import statistics
    # Filter out None scores
    cosine_scores_correct = [s for s in cosine_scores_correct if s is not None]
    cosine_scores_incorrect = [s for s in cosine_scores_incorrect if s is not None]
    avg_correct = statistics.mean(cosine_scores_correct) if cosine_scores_correct else 0
    avg_incorrect = statistics.mean(cosine_scores_incorrect) if cosine_scores_incorrect else 0

    # Point-biserial correlation (simplified: difference in means)
    score_correlation = avg_correct - avg_incorrect  # positive means higher scores correlate with correctness

    return {
        "total_claims": total,
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "avg_cosine_correct": round(avg_correct, 4),
        "avg_cosine_incorrect": round(avg_incorrect, 4),
        "cosine_correlation_diff": round(score_correlation, 4),
        "claim_details": claim_results
    }


def run_evaluation():
    """Run the custom verification evaluation."""
    print("=" * 80)
    print("CUSTOM VERIFICATION AGENT EVALUATION")
    print("=" * 80)

    results = evaluate_verification_accuracy()

    print(f"\nTotal claims evaluated: {results['total_claims']}")
    print(f"True Positives:  {results['true_positives']}")
    print(f"False Positives: {results['false_positives']}")
    print(f"True Negatives:  {results['true_negatives']}")
    print(f"False Negatives: {results['false_negatives']}")
    print(f"\nAccuracy:  {results['accuracy']:.4f}")
    print(f"Precision: {results['precision']:.4f}")
    print(f"Recall:    {results['recall']:.4f}")
    print(f"F1 Score:  {results['f1']:.4f}")
    print(f"\nAvg cosine (correct):    {results['avg_cosine_correct']:.4f}")
    print(f"Avg cosine (incorrect):  {results['avg_cosine_incorrect']:.4f}")
    print(f"Correlation diff:        {results['cosine_correlation_diff']:.4f}")

# Per-claim details
    print("\n--- Per-Claim Results ---")
    for c in results["claim_details"]:
        status = "PASS" if c["correct"] else "FAIL"
        score_str = f"{c['cosine_score']:.4f}" if c["cosine_score"] is not None else "N/A"
        print(f"  {status} {c['claim_id'][:8]}... grounded={c['predicted_grounded']} truth={c['ground_truth']} score={score_str}")

    # Save results
    output_dir = Path("eval/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"verification_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    output_data = {
        "timestamp": datetime.now().isoformat(),
        "total_claims": results["total_claims"],
        "metrics": {
            "accuracy": results["accuracy"],
            "precision": results["precision"],
            "recall": results["recall"],
            "f1": results["f1"],
            "avg_cosine_correct": results["avg_cosine_correct"],
            "avg_cosine_incorrect": results["avg_cosine_incorrect"],
            "cosine_correlation_diff": results["cosine_correlation_diff"],
        },
        "confusion_matrix": {
            "tp": results["true_positives"],
            "fp": results["false_positives"],
            "tn": results["true_negatives"],
            "fn": results["false_negatives"],
        },
        "claims": results["claim_details"]
    }

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    return results


if __name__ == "__main__":
    run_evaluation()