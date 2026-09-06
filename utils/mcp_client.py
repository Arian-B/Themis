import asyncio
import json
import logging
import sys
import os
from typing import Any

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

logger = logging.getLogger(__name__)

async def _call_mcp_tool_async(server_script: str, tool_name: str, arguments: dict) -> str:
    """Async implementation to call an MCP tool via stdio."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=dict(os.environ)
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.call_tool(tool_name, arguments)
                if not result.content:
                    return ""
                    
                # We expect the text to be in the first content block
                for block in result.content:
                    if block.type == "text":
                        return block.text
                        
                return ""
    except Exception as e:
        logger.error(f"Error calling MCP tool '{tool_name}' on server '{server_script}': {e}")
        return json.dumps({"error": str(e)})

def call_mcp_tool(server_script: str, tool_name: str, arguments: dict) -> str:
    """
    Synchronously call an MCP tool, handling both cases:
    - Called from sync context (no running event loop) -> use asyncio.run()
    - Called from async context (running event loop) -> run on existing loop
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running event loop, safe to use asyncio.run()
        return asyncio.run(_call_mcp_tool_async(server_script, tool_name, arguments))
    
    # Running inside an event loop (e.g., FastAPI background task)
    # Schedule the coroutine on the existing loop and wait for it
    return loop.run_until_complete(_call_mcp_tool_async(server_script, tool_name, arguments))
