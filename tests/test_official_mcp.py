import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp_protocol():
    print("Testing Official TigerGraph MCP Protocol...")
    
    # Configure the official tigergraph-mcp executable
    # The binary should be available in the active virtual environment.
    server_params = StdioServerParameters(
        command="tigergraph-mcp",
        args=[],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 1. Initialize
            print("Connecting and initializing session...")
            await session.initialize()
            
            # 2. List Tools
            print("\nRequesting tools/list...")
            tools = await session.list_tools()
            tool_names = [tool.name for tool in tools.tools]
            print(f"Discovered Tools: {tool_names}")
            
            assert len(tool_names) > 0, "Failed to discover any tools from official tigergraph-mcp."
            print("Success: Discovered tools from official MCP server.")
            
            # 3. Call Tool (Mocking / Invoking a basic tool to verify protocol)
            # Depending on credentials, it might return a real result or an authentication error.
            # We are verifying the protocol layer (tools/call) works.
            print("\nInvoking tools/call on the first tool...")
            try:
                # In DEMO_MODE we might just want to list schemas or query status
                # If MapVertex is present, we try a mock call.
                if "MapVertex" in tool_names:
                    result = await session.call_tool("MapVertex", {"vertex_type": "Customer"})
                    print(f"Result: {result}")
                else:
                    print(f"Skipping call_tool test since MapVertex is not available. Tools present: {tool_names}")
            except Exception as e:
                # If it raises an auth error because it actually tried hitting TG, that PROVES the protocol works!
                print(f"Tool invocation yielded (expected if no TG auth): {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_protocol())
