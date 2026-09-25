import asyncio
import os
import sys
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

async def test_real_tigergraph():
    print("Testing Real TigerGraph Connectivity via Official MCP...")
    
    # Check if credentials are supplied
    tg_host = os.environ.get("TG_HOST")
    tg_username = os.environ.get("TG_USERNAME")
    
    if not tg_host or not tg_username:
        print("Skipping Real Graph test: TG_HOST and TG_USERNAME must be set.")
        sys.exit(0)
        
    print(f"Connecting to TG_HOST: {tg_host}")
    
    server_params = StdioServerParameters(
        command="tigergraph-mcp",
        args=[],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Use the official MapVertex or RunInstalledQuery tool to fetch real data
            tools = await session.list_tools()
            tool_names = [tool.name for tool in tools.tools]
            
            assert "tigergraph__run_installed_query" in tool_names, "tigergraph__run_installed_query tool missing from MCP server."
            
            print("\nExecuting real graph query (get_transaction_context)...")
            try:
                result = await session.call_tool("tigergraph__run_installed_query", {
                    "query_name": "get_transaction_context",
                    "params": {"txn_id": "3514030"}
                })
                print(f"Successfully retrieved real graph data: {result.content}")
            except Exception as e:
                print(f"Error querying real graph: {e}")
                sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_real_tigergraph())
