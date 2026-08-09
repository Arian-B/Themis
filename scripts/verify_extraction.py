#!/usr/bin/env python
"""
scripts/verify_extraction.py — Validate extraction grounding.

Reads the SaaS MSA, runs extraction, and verifies that every claimed
section_reference actually exists in the raw text. This proves the LLM
is grounding its extraction, not hallucinating generic section titles.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

logging.getLogger("agents").setLevel(logging.WARNING)

def run_verification(doc_id: str):
    jsonl_path = ROOT / "data" / "raw" / "themis_edgar_contracts.jsonl"
    docs = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    
    target_doc = next((d for d in docs if d["doc_id"] == doc_id), None)
    if not target_doc:
        sys.exit(f"Contract {doc_id} not found.")

    raw_text = target_doc["text"]
    
    from graph.build import build_graph
    graph = build_graph()
    
    print(f"Running extraction on doc {doc_id}...\n")
    result = graph.invoke({
        "contract_id": doc_id,
        "tenant_id": "test",
        "session_id": str(uuid.uuid4()),
        "raw_text": raw_text,
        "errors": [],
    })
    
    ext = result.get("extraction_result", {})
    clauses = ext.get("clauses", [])
    
    print(f"Extracted {len(clauses)} clauses. Verifying grounding:\n")
    print("-" * 80)
    
    hallucinations = 0
    for i, c in enumerate(clauses, 1):
        ref = c.get("section_reference", "")
        text_preview = c.get("text", "")[:60].replace('\n', ' ')
        
        # Check if the exact section reference string appears anywhere in the raw text
        found = ref in raw_text
        
        print(f"Clause {i:02d} | Type: {c.get('clause_type'):>15}")
        if found:
            print(f"  [GROUNDED] Reference: '{ref}'")
        else:
            print(f"  [WARNING]  Reference: '{ref}' NOT FOUND IN RAW TEXT (Hallucination?)")
            hallucinations += 1
            
        print(f"  [PREVIEW]  {text_preview}...")
        print("-" * 80)
        
    if hallucinations > 0:
        print(f"\nFAILED: Found {hallucinations} ungrounded section references.")
    else:
        print("\nSUCCESS: All section references are grounded in the raw text.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract-id", type=str, help="Specific doc ID to run")
    args = parser.parse_args()

    if args.contract_id:
        run_verification(args.contract_id)
    else:
        jsonl_path = ROOT / "data" / "raw" / "themis_edgar_contracts.jsonl"
        docs = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for d in docs:
            run_verification(d["doc_id"])

