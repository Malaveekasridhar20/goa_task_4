import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def get_schema():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    server_params = StdioServerParameters(command="tigergraph-mcp", args=[], env=os.environ.copy())
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            res = await session.call_tool("tigergraph__get_graph_schema", {"graph_name": "Transaction_Fraud"})
            print(res.content[0].text)

if __name__ == "__main__":
    asyncio.run(get_schema())
