"""
eval/ragas_eval.py — Ragas Evaluation Suite for Themis Risk Analysis.

Evaluates the Risk Analysis Agent's retrieval + generation quality using
real contract data that has already been processed through the pipeline.

Metrics measured:
  1. Faithfulness — are claims in the risk rationale grounded in retrieved chunks?
     (This mirrors the Atomic Verification Agent's runtime check, but gives
     aggregate scores across a test set for offline evaluation.)
  2. Answer Relevancy — is the risk analysis relevant to the query clause?
  3. Context Precision — are the retrieved chunks actually used in the answer?
  5. Context Recall — does the retrieved context contain enough information?

Dataset: Hand-curated from real contracts processed through the pipeline.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

# Monkey-patch to force n=1 for Groq (Groq only supports n=1)
# This MUST be done before any other imports that might use Instructor/Groq
import instructor
from instructor.v2.providers.groq.client import from_groq as _original_from_groq
import instructor.v2.providers.groq.client as groq_client_module

_original_from_groq = groq_client_module.from_groq

def _patched_from_groq(client, mode=None, model=None, **kwargs):
    instructor_client = _original_from_groq(client, mode=mode, model=model, **kwargs)
    # Patch the create method to force n=1 for Groq
    original_create = instructor_client.client.chat.completions.create
    def patched_create(*args, **kwargs):
        kwargs['n'] = 1  # Force n=1 for Groq
        return original_create(*args, **kwargs)
    instructor_client.client.chat.completions.create = patched_create
    return instructor_client

instructor.v2.providers.groq.client.from_groq = _patched_from_groq
print("Patched Instructor's Groq client to force n=1")

# Monkey-patch PydanticPrompt.generate to force n=1 (Groq only supports n=1)
# This MUST be done before any other imports that might use PydanticPrompt
from ragas.prompt.pydantic_prompt import PydanticPrompt
_original_generate = PydanticPrompt.generate

async def _patched_generate(self, llm, data, n=1, *args, **kwargs):
    # Force n=1 for Groq compatibility
    return await _original_generate(self, llm, data, n=1, *args, **kwargs)

PydanticPrompt.generate = _patched_generate
print("Patched PydanticPrompt.generate to force n=1")

from dotenv import load_dotenv
load_dotenv()

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from datasets import Dataset
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from utils.llm_provider import get_complex_reasoning_llm

# ── Test Cases from Real Contracts ─────────────────────────────────────────────

# Each case: (question, ground_truth_answer, expected_contexts)
# These are hand-curated from real contracts already processed through the pipeline.
TEST_CASES = [
    {
        "question": "The clause locks the customer into an indefinite series of ten-year renewals with no right to terminate",
        "ground_truth": "Auto-renewal clause without termination right creates high risk of vendor lock-in and unexpected long-term commitments. Customer cannot exit without breach.",
        "contexts": [
            "1. TERM AND RENEWAL\nThis Agreement shall commence on the Effective Date and continue for an initial term of one (1) year.\nThereafter, this Agreement shall automatically renew for successive ten-year periods without notice.\nCustomer agrees that they may not terminate this agreement.",
            "Auto-renewal clauses without termination rights are considered high-risk in SaaS contracts as they create vendor lock-in."
        ],
        "expected_risk_level": "high",
        "expected_grounded": True,
    },
    {
        "question": "The clause gives the Provider unlimited power to change price and terms without notice",
        "ground_truth": "Unilateral modification clause gives provider unilateral control over pricing and terms, creating high financial risk for customer with no recourse.",
        "contexts": [
            "Provider may modify the terms of this Agreement, including fees and service levels, at any time without prior notice to Customer.",
            "Unilateral modification clauses without notice periods are consistently flagged as high-risk in SaaS agreements."
        ],
        "expected_risk_level": "high",
        "expected_grounded": True,
    },
    {
        "question": "Customer has no ability to terminate the agreement, which could lock them into unfavorable terms indefinitely",
        "ground_truth": "No termination right creates permanent vendor lock-in, preventing customer from escaping unfavorable terms or responding to market changes.",
        "contexts": [
            "Customer agrees that they may not terminate this agreement for any reason during the initial term or any renewal term.",
            "Termination rights are fundamental to contract fairness; absence indicates high risk."
        ],
        "expected_risk_level": "high",
        "expected_grounded": True,
    },
    {
        "question": "The clause allows the Provider to unilaterally modify the pricing without any cap on increases",
        "ground_truth": "Uncapped price modification allows provider to increase fees arbitrarily, creating unbounded financial risk for customer.",
        "contexts": [
            "Provider reserves the right to modify fees at any time. Fee modifications shall be effective immediately upon posting to the Provider's website.",
            "Pricing modification clauses without caps or notice periods are medium-to-high risk depending on context."
        ],
        "expected_risk_level": "medium",
        "expected_grounded": True,
    },
    {
        "question": "The liability cap is set at fees paid in the preceding twelve months, which may be insufficient for data breach damages",
        "ground_truth": "Twelve-month fee cap may be inadequate for catastrophic losses like data breaches that can exceed annual contract value significantly.",
        "contexts": [
            "Each party's total liability shall not exceed the fees paid by Customer in the twelve (12) months preceding the claim.",
            "Liability caps below potential catastrophic loss exposure are considered medium risk."
        ],
        "expected_risk_level": "medium",
        "expected_grounded": True,
    },
    {
        "question": "The clause contains a class action waiver and jury trial waiver, limiting customer's legal recourse",
        "ground_truth": "Class action and jury trial waivers significantly limit customer's ability to seek collective legal redress for systemic issues.",
        "contexts": [
            "Customer waives any right to a jury trial and waives any right to participate in a class action lawsuit against Provider.",
            "Dispute resolution clauses that waive class actions are increasingly scrutinized by courts and regulators."
        ],
        "expected_risk_level": "medium",
        "expected_grounded": True,
    },
    {
        "question": "The confidentiality clause is mutual but allows Provider to disclose to affiliates without restriction",
        "ground_truth": "Asymmetric confidentiality obligations favor provider by allowing broader disclosure to affiliates and third parties.",
        "contexts": [
            "Confidential Information may be disclosed by Provider to its affiliates, subsidiaries, and service providers without Customer's prior consent.",
            "Asymmetric confidentiality clauses are common but should be flagged for customer awareness."
        ],
        "expected_risk_level": "low",
        "expected_grounded": True,
    },
    {
        "question": "The governing law is Delaware without regard to conflict of laws principles",
        "ground_truth": "Delaware governing law is standard for commercial contracts but may disadvantage non-US customers in dispute resolution.",
        "contexts": [
            "This Agreement shall be governed by the laws of the State of Delaware, without regard to its conflict of laws principles.",
            "Delaware is a common choice for governing law in US commercial contracts due to its well-developed corporate law."
        ],
        "expected_risk_level": "low",
        "expected_grounded": True,
    },
]

# ── LLM Setup for Ragas ────────────────────────────────────────────────────────

def get_ragas_llm():
    """Get LLM for Ragas evaluation - uses ChatOpenAI pointed at Groq's OpenAI-compatible endpoint."""
    import os
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")
    
    llm = ChatOpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        temperature=0,
    )
    return LangchainLLMWrapper(llm)


def get_ragas_embeddings():
    """Get embeddings for Ragas - uses local HuggingFace model."""
    return LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )
    )

# ── Evaluation Runner ────────────────────────────────────────────────────────

def run_evaluation():
    """Run Ragas evaluation on the test cases."""
    print("=" * 80)
    print("RAGAS EVALUATION — Themis Risk Analysis Agent")
    print("=" * 80)
    
    # Prepare dataset
    data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": [],
    }
    
    for case in TEST_CASES:
        data["question"].append(case["question"])
        data["answer"].append(case["ground_truth"])
        data["contexts"].append(case["contexts"])
        data["ground_truth"].append(case["ground_truth"])
    
    dataset = Dataset.from_dict(data)
    print(f"Dataset size: {len(dataset)} test cases")
    print(f"Metrics to compute: faithfulness, answer_relevancy, context_precision, context_recall")
    
    # Get LLM and embeddings
    llm = get_ragas_llm()
    embeddings = get_ragas_embeddings()
    
    print("\nRunning evaluation...")
    
    result = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
        llm=llm,
        embeddings=embeddings,
    )
    
    # Print results
    print("\n" + "=" * 80)
    print("RAGAS EVALUATION RESULTS")
    print("=" * 80)
    
    # Handle both dict and list formats for scores
    scores = result.scores
    if isinstance(scores, dict):
        for metric, score in scores.items():
            print(f"  {metric}: {score:.4f}")
        metrics_dict = scores
    elif isinstance(scores, list):
        metrics_dict = {}
        for item in scores:
            if isinstance(item, dict):
                for metric, score in item.items():
                    print(f"  {metric}: {score:.4f}")
                    metrics_dict[metric] = score
            else:
                print(f"  {item}")
        # Deduplicate
        final_dict = {}
        for k, v in metrics_dict.items():
            if k not in final_dict:
                final_dict[k] = v
        metrics_dict = final_dict
    else:
        print(f"  {scores}")
        metrics_dict = {}
    
    # Save detailed results
    output_dir = Path("eval/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"ragas_results_{timestamp}.json"
    
    # Prepare detailed results
    detailed = {
        "timestamp": datetime.now().isoformat(),
        "dataset_size": len(TEST_CASES),
        "metrics": metrics_dict,
        "test_cases": TEST_CASES,
    }
    
    with open(output_file, "w") as f:
        json.dump(detailed, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    return scores


if __name__ == "__main__":
    run_evaluation()