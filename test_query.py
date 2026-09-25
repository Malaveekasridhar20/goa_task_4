import asyncio, os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run():
    server_params = StdioServerParameters(command='tigergraph-mcp', args=[], env=os.environ.copy())
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            res = await session.call_tool('tigergraph__get_node', {'vertex_type': 'Payment_Transaction', 'vertex_id': '3514030', 'graph_name': 'Transaction_Fraud'})
            print(res.content[0].text)

if __name__ == "__main__":
    asyncio.run(run())
