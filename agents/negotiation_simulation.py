"""
agents/negotiation_simulation.py — Agent 6: Negotiation Simulation
"""

from __future__ import annotations

import logging
import json
from typing import Annotated, Any, Literal, Optional
from typing_extensions import TypedDict
import operator

from langgraph.graph import END, START, StateGraph
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from graph.state import ThemisState
from schemas.negotiation import NegotiationTurn, NegotiationTranscript
from utils.llm_provider import get_complex_reasoning_llm

logger = logging.getLogger(__name__)

class NegotiationState(TypedDict):
    clause_id: str
    original_text: str
    concern: str
    turns: Annotated[list[dict[str, Any]], operator.add]
    outcome: Optional[Literal["agreement_reached", "impasse", "max_turns_reached"]]


_PROPOSER_PROMPT = """\
You are the "proposer" (our client's counsel). 
You need to revise the following contract clause to mitigate this concern:
Concern: {concern}

Original Text: {original_text}

Here is the negotiation history so far:
{history}

If the counterparty has provided a redline, evaluate it. If it fully resolves your concern, output "AGREEMENT_REACHED".
Otherwise, propose a new redline that compromises while still addressing your core concern.

Respond ONLY with a JSON object exactly matching this schema:
{{
  "proposed_text": "<Your proposed text>",
  "rationale": "<Your legal rationale>",
  "is_agreement": true/false
}}
"""

_COUNTERPARTY_PROMPT = """\
You are the "counterparty" counsel. 
You are receiving a proposed redline from the other side.
Original Text: {original_text}

Here is the negotiation history so far:
{history}

Evaluate the proposer's latest redline. If it is commercially reasonable and protects your client, output "AGREEMENT_REACHED".
Otherwise, push back by proposing your own redline that protects your client's original position.

Respond ONLY with a JSON object exactly matching this schema:
{{
  "proposed_text": "<Your proposed text>",
  "rationale": "<Your legal rationale>",
  "is_agreement": true/false
}}
"""


def _invoke_and_parse(system_prompt: str, human_prompt: str) -> dict:
    llm = get_complex_reasoning_llm(temperature=0.2)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]
    resp = llm.invoke(messages)
    text = resp.content if hasattr(resp, "content") else str(resp)
    
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:-1]) if len(lines) > 2 else clean
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON in negotiation: {text}")
        return {"proposed_text": text[:100], "rationale": "Parse error", "is_agreement": False}


def proposer_node(state: NegotiationState) -> dict:
    logger.info("ENTERED NODE: proposer")
    history_str = ""
    turns = state.get("turns", [])
    for t in turns:
        history_str += f"{t['speaker'].upper()}:\nText: {t['proposed_text']}\nRationale: {t['rationale']}\n\n"
        
    prompt = _PROPOSER_PROMPT.format(
        concern=state["concern"],
        original_text=state["original_text"],
        history=history_str or "No history yet. Propose the first redline."
    )
    
    res = _invoke_and_parse(prompt, "Your turn.")
    
    if res.get("is_agreement") and turns:
        return {"outcome": "agreement_reached"}
        
    turn = {
        "turn_number": len(turns) + 1,
        "speaker": "proposer",
        "proposed_text": res.get("proposed_text", ""),
        "rationale": res.get("rationale", "")
    }
    return {"turns": [turn]}


def counterparty_node(state: NegotiationState) -> dict:
    logger.info("ENTERED NODE: counterparty")
    history_str = ""
    turns = state.get("turns", [])
    for t in turns:
        history_str += f"{t['speaker'].upper()}:\nText: {t['proposed_text']}\nRationale: {t['rationale']}\n\n"
        
    prompt = _COUNTERPARTY_PROMPT.format(
        original_text=state["original_text"],
        history=history_str
    )
    
    res = _invoke_and_parse(prompt, "Your turn.")
    
    if res.get("is_agreement"):
        return {"outcome": "agreement_reached"}
        
    turn = {
        "turn_number": len(turns) + 1,
        "speaker": "counterparty",
        "proposed_text": res.get("proposed_text", ""),
        "rationale": res.get("rationale", "")
    }
    return {"turns": [turn]}


def route_negotiation(state: NegotiationState) -> str:
    if state.get("outcome") == "agreement_reached":
        return END
    
    turns = state.get("turns", [])
    if len(turns) >= 4:
        return END
        
    last_speaker = turns[-1]["speaker"] if turns else None
    if last_speaker == "proposer":
        return "counterparty"
    else:
        return "proposer"

def build_negotiation_graph():
    builder = StateGraph(NegotiationState)
    builder.add_node("proposer", proposer_node)
    builder.add_node("counterparty", counterparty_node)
    
    builder.add_edge(START, "proposer")
    
    builder.add_conditional_edges(
        "proposer",
        route_negotiation,
        {
            "counterparty": "counterparty",
            END: END
        }
    )
    
    builder.add_conditional_edges(
        "counterparty",
        route_negotiation,
        {
            "proposer": "proposer",
            END: END
        }
    )
    
    return builder.compile()

negotiation_graph = build_negotiation_graph()

def run_negotiation_node(state: ThemisState) -> dict:
    """
    Called from main graph if a human override demands negotiation.
    """
    logger.info("Starting negotiation simulation...")
    overrides = state.get("human_override", {}).get("overrides", [])
    if not overrides:
        return {}
        
    # Find a flag with a negotiation request (for this task, we will just pick the first accepted override)
    target_idx = None
    for ov in overrides:
        if ov.get("status") == "accepted":
            target_idx = ov.get("flag_index")
            break
            
    if target_idx is None:
        return {}
        
    flags = state.get("risk_analysis_result", [])
    if target_idx >= len(flags):
        return {}
        
    flag = flags[target_idx]
    
    # We need the original text
    clause_id = flag.get("clause_id")
    raw_text = ""
    ext_result = state.get("extraction_result", {}).get("clauses", [])
    for c in ext_result:
        if c.get("clause_id") == clause_id:
            raw_text = c.get("text", "")
            break
            
    sub_state = {
        "clause_id": clause_id,
        "original_text": raw_text,
        "concern": flag.get("concern", ""),
        "turns": []
    }
    
    # Run subgraph
    res = negotiation_graph.invoke(sub_state)
    
    outcome = res.get("outcome")
    turns = res.get("turns", [])
    
    if not outcome:
        if len(turns) >= 4:
            outcome = "max_turns_reached"
        else:
            outcome = "impasse"
            
    transcript = {
        "clause_id": clause_id,
        "turns": turns,
        "outcome": outcome
    }
    
    return {"negotiation_transcript": transcript}
