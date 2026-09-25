import asyncio, os, io
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run():
    server_params = StdioServerParameters(command='tigergraph-mcp', args=[], env=os.environ.copy())
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            with io.open('scratch_tools.txt', 'w', encoding='utf-8') as f:
                for tool in tools.tools:
                    f.write(tool.name + '\n')

if __name__ == "__main__":
    asyncio.run(run())
