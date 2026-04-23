import asyncio
import json
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Explicit mapping of the 4 MCP servers as per your project structure
# Note: Keeping the 'webserch_mcp.py' spelling as requested.
SERVERS = {
    "filesystem": "mcp_servers/filesystem_mcp.py",
    "websearch": "mcp_servers/webserch_mcp.py",
    "gdrive": "mcp_servers/gdrive_mcp.py",
    "notion": "mcp_servers/notion_mcp.py",
}

def _decode_content(result) -> object:
    """Helper to parse the multi-block content returned by MCP servers."""
    if not getattr(result, "content", None):
        return {"error": "No result returned from server"}

    pieces = []
    for block in result.content:
        text = getattr(block, "text", None)
        if text is None:
            text = str(block)
        pieces.append(text)

    payload = "\n".join(pieces).strip()

    try:
        # Attempt to parse JSON if the tool returns a stringified dict/list
        return json.loads(payload)
    except Exception:
        # Fallback for plain text results (like protocol content)
        return payload

async def _call_tool(server_name: str, tool_name: str, arguments: dict) -> object:
    """Internal async logic to spawn the MCP process and execute the tool."""
    server_path = SERVERS.get(server_name)
    if not server_path:
        return {"error": f"Server '{server_name}' is not registered in client.py"}

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_path],
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return _decode_content(result)
    except Exception as e:
        return {"error": f"MCP Error on {server_name}/{tool_name}: {str(e)}"}

def call_tool(server_name: str, tool_name: str, arguments: dict) -> object:
    """Synchronous wrapper to allow Streamlit threads to call async MCP functions."""
    return asyncio.run(_call_tool(server_name, tool_name, arguments))

async def _list_tools(server_name: str) -> list:
    """Internal async logic to list tools available on a specific server."""
    server_path = SERVERS.get(server_name)
    if not server_path:
        return [{"error": f"Unknown server: {server_name}"}]

    server_params = StdioServerParameters(command=sys.executable, args=[server_path])
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [{"name": t.name, "description": t.description} for t in tools.tools]
    except Exception as e:
        return [{"error": str(e)}]

def list_server_tools(server_name: str) -> list:
    """Synchronous wrapper for listing tools."""
    return asyncio.run(_list_tools(server_name))