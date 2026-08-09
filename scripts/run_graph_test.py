#!/usr/bin/env python
"""
scripts/run_graph_test.py — Manual CLI entry point for Day 2 graph end-to-end test.

Usage:
    python scripts/run_graph_test.py
    python scripts/run_graph_test.py --contract-id 432d3442fb4aab3b6380f29ba00cbf05
    python scripts/run_graph_test.py --raw-text "This is not a real contract. It's just garbage text to test fallback."
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Load .env before any other imports that read env vars
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("agents").setLevel(logging.INFO)
logging.getLogger("graph").setLevel(logging.INFO)


def load_contract_by_id(contract_id: str) -> dict:
    jsonl_path = ROOT / "data" / "raw" / "themis_edgar_contracts.jsonl"
    if not jsonl_path.exists():
        sys.exit(f"ERROR: {jsonl_path} not found.")

    docs = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    doc = next((d for d in docs if d.get("doc_id") == contract_id), None)
    
    if not doc:
        sys.exit(f"ERROR: Contract ID {contract_id} not found in corpus.")
        
    print(f"\n{'='*70}")
    print(f"CONTRACT: {doc['title']}")
    print(f"Type:     {doc['document_type']}")
    print(f"Length:   {len(doc['text'])} characters")
    print(f"Doc ID:   {doc['doc_id']}")
    print(f"{'='*70}\n")
    return doc


def run(contract_id: str | None = None, raw_text: str | None = None) -> None:
    from graph.build import build_graph
    from graph.state import ThemisState
    
    if raw_text:
        doc_id = "garbage-test"
        text = raw_text
        print(f"\n{'='*70}")
        print("RUNNING WITH ARBITRARY RAW TEXT")
        print(f"Length:   {len(text)} characters")
        print(f"{'='*70}\n")
    else:
        # Default to SaaS MSA if nothing provided
        c_id = contract_id or "432d3442fb4aab3b6380f29ba00cbf05"
        doc = load_contract_by_id(c_id)
        doc_id = doc["doc_id"]
        text = doc["text"]

    graph = build_graph()

    initial_state: ThemisState = {
        "contract_id": doc_id,
        "tenant_id": "test_tenant",
        "session_id": str(uuid.uuid4()),
        "raw_text": text,
        "errors": [],
    }

    print("Running graph: START -> jurisdiction_classifier -> extraction_agent -> END")
    result = graph.invoke(initial_state)

    # ── Jurisdiction Result ────────────────────────────────────────────────────
    jur = result.get("jurisdiction_result") or {}
    print("\n" + "-" * 70)
    print("JURISDICTION CLASSIFICATION")
    print("-" * 70)
    print(f"  Jurisdiction:  {jur.get('jurisdiction', 'N/A')}")
    print(f"  Confidence:    {jur.get('confidence', 0):.0%}")
    print(f"  Fallback used: {jur.get('fallback_used', False)}")
    print(f"  Reasoning:     {jur.get('reasoning', 'N/A')}")

    # ── Extraction Result ──────────────────────────────────────────────────────
    ext = result.get("extraction_result") or {}
    clauses = ext.get("clauses", [])
    print(f"\n{'-' * 70}")
    print(f"EXTRACTION RESULT — {len(clauses)} clauses extracted")
    print("-" * 70)

    for i, clause in enumerate(clauses, 1):
        ct = clause.get("clause_type", "?")
        section = clause.get("section_reference", "?")
        print(f"  {i:2d}. [{ct:>16}] {section}")

    # ── Errors ─────────────────────────────────────────────────────────────────
    errors = result.get("errors") or []
    if errors:
        print(f"\n{'-' * 70}")
        print(f"ERRORS ({len(errors)} recorded):")
        for e in errors:
            print(f"  [{e.get('node')}] {e.get('error_type')}: {e.get('message')[:120]}")

    print(f"\n{'='*70}")
    print("DONE")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Themis Day 2 graph")
    parser.add_argument("--contract-id", type=str, help="Doc ID of contract to run")
    parser.add_argument("--raw-text", type=str, help="Literal string to process as raw text")
    args = parser.parse_args()
    
    if args.contract_id and args.raw_text:
        sys.exit("Error: Cannot provide both --contract-id and --raw-text")
        
    run(contract_id=args.contract_id, raw_text=args.raw_text)
