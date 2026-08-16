"""
tools/mcp/jurisdiction_router_server.py — MCP server wrapping jurisdiction classification logic.
"""

import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path if not already there
ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP
from langchain_core.messages import HumanMessage, SystemMessage

# Since this MCP server can run independently, we define the LLM logic here or import it
# For simplicity, we import the exact same LLM utility
try:
    from utils.llm_provider import get_complex_reasoning_llm
except ImportError:
    pass

logger = logging.getLogger(__name__)

mcp = FastMCP("themis-jurisdiction-router")

_SYSTEM_PROMPT = """\
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

_CORRECTION_PROMPT = """\
Your previous response could not be parsed as valid JSON matching the required schema.

Validation error: {error}

Your previous response:
{previous_response}

Respond ONLY with a corrected JSON object — no prose, no markdown fences.
"""

def _build_llm():
    # We use the same Ollama model as extraction (fast, local)
    import os
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model="llama3.1:8b",
        base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        temperature=0,
        format="json",
    )

def _invoke_llm(llm, messages: list, attempt: int) -> str:
    try:
        response = llm.invoke(messages)
        return response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        logger.warning("LLM invocation error on attempt %d: %s", attempt, exc)
        return ""

@mcp.tool()
def classify_jurisdiction(text: str) -> str:
    """
    Determine the governing law of a contract based on its text.
    
    Args:
        text: The first few pages of the contract text.
        
    Returns:
        JSON string containing jurisdiction classification schema.
    """
    if not text:
        return json.dumps({"error": "Empty text provided"})
        
    llm = _build_llm()
    prompt_text = f"CONTRACT TEXT TO ANALYZE:\n{text}"
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=prompt_text),
    ]

    # Attempt 1
    raw = _invoke_llm(llm, messages, attempt=1)
    if not raw.strip():
        return json.dumps({"error": "Empty response from LLM"})
        
    # We let the caller parse the JSON and handle ValidationError.
    # We just do a basic JSON clean here.
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:-1]) if len(lines) > 2 else clean
        
    # Validate basic JSON structure
    try:
        json.loads(clean)
        return clean
    except json.JSONDecodeError as e:
        # Attempt 2
        correction = _CORRECTION_PROMPT.format(error=str(e), previous_response=raw)
        messages.append(HumanMessage(content=correction))
        raw2 = _invoke_llm(llm, messages, attempt=2)
        
        clean2 = raw2.strip()
        if clean2.startswith("```"):
            lines = clean2.split("\n")
            clean2 = "\n".join(lines[1:-1]) if len(lines) > 2 else clean2
            
        try:
            json.loads(clean2)
            return clean2
        except json.JSONDecodeError as e2:
            return json.dumps({"error": f"JSON parse error after 2 attempts: {e2}"})

if __name__ == "__main__":
    mcp.run()
