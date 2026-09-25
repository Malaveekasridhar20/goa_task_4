import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()

async def run():
    server_params = StdioServerParameters(command='tigergraph-mcp', args=[], env=os.environ.copy())
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            res = await session.call_tool('tigergraph__show_graph_details', {'graph_name': 'Transaction_Fraud'})
            with open('scratch_details.txt', 'w', encoding='utf-8') as f:
                f.write(res.content[0].text)

if __name__ == '__main__':
    asyncio.run(run())
