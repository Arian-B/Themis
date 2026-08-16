#!/usr/bin/env python
"""
Isolation test for jurisdiction_classifier — runs the node alone on the SaaS MSA,
prints the raw LLM response text before parsing so we can see exactly what Groq returns.
"""
import sys
import json
import logging
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")

from langchain_core.messages import HumanMessage, SystemMessage
from utils.llm_provider import get_complex_reasoning_llm

# Load SaaS MSA raw text
jsonl_path = ROOT / "data" / "raw" / "themis_edgar_contracts.jsonl"
docs = [json.loads(l) for l in jsonl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
doc = next(d for d in docs if d["doc_id"] == "432d3442fb4aab3b6380f29ba00cbf05")
raw_text = doc["text"][:3000]

SYSTEM_PROMPT = """\
You are a legal jurisdiction classifier. Your task is to determine the governing law
of a contract based on its text.

Supported jurisdictions:
  - "us_generic" — United States law (any US state, or unspecified US law)
  - "uk"         — English, Welsh, or Scottish law

Rules:
  1. Look for an explicit "Governing Law" or "Choice of Law" clause.
  2. If found, extract its verbatim text and set jurisdiction accordingly.
  3. If no explicit clause, infer from terminology (e.g. "Company Acts", "Corporations Act").
  4. Default to "us_generic" if ambiguous. Set fallback_used=true in that case.
  5. Confidence: 0.9–1.0 if governing-law clause found, 0.5–0.8 for inferred, 0.3–0.5 if fallback.

You MUST respond with ONLY a JSON object — no prose, no markdown, no explanation.
The JSON object must match this exact schema:
{
  "jurisdiction": "us_generic" | "uk",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<one to three sentences explaining the determination>",
  "governing_law_clause_text": "<verbatim clause text or null>",
  "fallback_used": <true|false>
}
"""

print("=" * 70)
print("JURISDICTION CLASSIFIER ISOLATION TEST")
print("=" * 70)

llm = get_complex_reasoning_llm(
    temperature=0,
    model_kwargs={"response_format": {"type": "json_object"}},
)

messages = [
    SystemMessage(content=SYSTEM_PROMPT),
    HumanMessage(content=f"Classify the governing law of this contract:\n\n{raw_text}"),
]

print("\n[*] Invoking LLM...")
try:
    response = llm.invoke(messages)
    raw = response.content
    print(f"\n[RAW LLM RESPONSE]:\n{raw}")
    print(f"\n[RESPONSE LENGTH]: {len(raw)} chars")

    # Try parsing
    data = json.loads(raw)
    print(f"\n[PARSED JSON]:")
    for k, v in data.items():
        print(f"  {k}: {v!r}")

    # Try Pydantic validation
    from schemas.jurisdiction import JurisdictionClassification
    result = JurisdictionClassification.model_validate(data)
    print(f"\n[PYDANTIC VALIDATION]: PASSED")
    print(f"  jurisdiction:  {result.jurisdiction}")
    print(f"  confidence:    {result.confidence}")
    print(f"  fallback_used: {result.fallback_used}")
    print(f"  reasoning:     {result.reasoning}")

except Exception as e:
    print(f"\n[ERROR]: {type(e).__name__}: {e}")
