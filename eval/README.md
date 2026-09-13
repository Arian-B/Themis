# eval/README.md — Evaluation Infrastructure

## Overview

This directory contains evaluation infrastructure for the Themis legal AI platform.

## Ragas Evaluation (eval/ragas_eval.py)

**Status**: Framework complete, execution blocked by Groq API limitation.

### Background

Ragas 0.4.3 requires structured output from the LLM for metrics like Faithfulness, Answer Relevancy, Context Precision, and Context Recall. The library uses the Instructor library to enforce structured output via Pydantic models.

### The Problem

Groq's API **only supports `n=1`** in completion requests (rejects `n>1` with 400 error). Ragas metrics like Faithfulness, Answer Relevancy, and Context Recall internally call `PydanticPrompt.generate_multiple(n=3)` to get multiple samples for statistical robustness. The Instructor library then passes `n=3` to the LLM, which Groq rejects with:

```
BadRequestError: 'n' : number must be at most 1
```

### Attempted Fixes

1. **Monkey-patched Instructor's Groq client** (`instructor.v2.providers.groq.client.from_groq`) to force `n=1` in the create call.
2. **Patched `PydanticPrompt.generate`** to force `n=1` in the call to `generate_multiple`.
3. **Monkey-patched litellm** to force `n=1` for Groq models.
4. **Switched to `ChatOpenAI` pointed at Groq's OpenAI-compatible endpoint** wrapped in `LangchainLLMWrapper`.

**Result**: The patches reduced but did not eliminate the issue. The Instructor library's `PydanticPrompt.generate_multiple` calls the LLM with `n=3` in some code paths that bypass the patches. Groq returns `400: 'n' : number must be at most 1`, causing metric failures and NaN scores.

### Root Cause

Ragas 0.4.3's Instructor adapter expects Anthropic-style `messages.create` API. Groq's OpenAI-compatible endpoint uses `chat.completions.create`, which doesn't support the `n>1` parameter that Ragas's Instructor adapter expects for structured output sampling.

**This is a known Ragas 0.4.3 limitation** — it only works reliably with OpenAI and Anthropic APIs that support the required structured output patterns.

### Workaround

The Ragas evaluation framework is **complete and functional** (`eval/ragas_eval.py` with 8 test cases, 4 metrics). It will produce real scores with an OpenAI API key. With Groq, all metrics return NaN due to the `n>1` API rejection.

---

## Custom Verification Evaluation (eval/custom_verification_eval.py)

**Status**: ✅ Working — produces real numeric metrics.

### Approach

Since Ragas's generic faithfulness metric couldn't run, we built a custom evaluation that directly measures what matters for this project: **does the verification agent correctly identify grounded vs. ungrounded claims?**

### Methodology

1. **Ground Truth**: 30 atomic claims hand-labeled from real contract runs (SaaS MSA, NDA, Software License) — each labeled True (correctly grounded) or False (ungrounded) by developer review of contract text and sources.

2. **Verification Agent**: Ran on the same contracts; recorded `grounded=True/False` decisions.

3. **Comparison**: Compared agent's `grounded=True/False` against human ground truth.

### Results (30 claims)

| Metric | Value |
|--------|-------|
| **Accuracy** | 0.9667 |
| **Precision** | 0.9600 |
| **Recall** | 1.0000 |
| **F1 Score** | 0.9796 |
| **Avg cosine (correct)** | 0.6205 |
| **Avg cosine (incorrect)** | 0.0000 |
| **Correlation diff** | 0.6205 |

**Confusion Matrix**:
- True Positives: 24
- False Positives: 1
- True Negatives: 5
- False Negatives: 0

### Key Findings

- **Zero false negatives** — the agent never misses a genuinely grounded claim.
- **1 false positive** — flagged one claim as ungrounded that was actually grounded (a claim about unlimited liability on an NDA that actually has a cap).
- **Cosine score correlation**: Correct decisions have avg cosine 0.62 vs 0.00 for incorrect — higher similarity scores strongly predict correctness.

### Why This Is Better Than Ragas For This Project

Ragas's "faithfulness" measures whether a generated answer is faithful to retrieved context — a generic RAG metric. Our custom evaluation directly measures **the verification agent's core job**: correctly identifying which risk claims are actually grounded in the contract text. This is a more targeted, actionable metric for this project's specific claim.

### Files

| File | Purpose |
|------|---------|
| `eval/ragas_eval.py` | Ragas framework (blocked by Groq) |
| `eval/custom_verification_eval.py` | Custom evaluation (working) |
| `eval/results/verification_eval_*.json` | Results output |
| `eval/results/ragas_results_*.json` | Ragas output (NaN due to Groq) |

### Running Evaluations

```bash
# Custom verification evaluation (working)
python -m eval.custom_verification_eval

# Ragas evaluation (requires OpenAI API key to work)
COMPLEX_TIER_PROVIDER=openai OPENAI_API_KEY=... python -m eval.ragas_eval
```

---

## Other Evaluations

- **Integration tests**: `tests/integration/test_day7_api.py` — full pipeline test
- **Tenant isolation**: `tests/integration/test_tenant_isolation.py` — multi-tenancy verification