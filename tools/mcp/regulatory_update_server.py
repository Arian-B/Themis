"""
tools/mcp/regulatory_update_server.py — MCP server for tracking regulatory updates.
"""

import json
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("themis-regulatory-update")

@mcp.tool()
def get_tracked_sources(jurisdiction: str) -> str:
    """
    Get a list of tracked regulatory sources for a given jurisdiction.
    
    Args:
        jurisdiction: The jurisdiction (e.g. 'us_generic' or 'uk').
        
    Returns:
        JSON string containing a list of source strings.
    """
    sources = {
        "us_generic": [
            "Securities and Exchange Commission (SEC) Edgar Database",
            "Federal Trade Commission (FTC) Updates",
            "Uniform Commercial Code (UCC) Reporter"
        ],
        "uk": [
            "Financial Conduct Authority (FCA) Handbook",
            "UK Legislation Database (legislation.gov.uk)",
            "Information Commissioner's Office (ICO) Guidance"
        ]
    }
    
    res = sources.get(jurisdiction.lower(), ["Generic/International Regulatory DB"])
    return json.dumps(res)

if __name__ == "__main__":
    mcp.run()
