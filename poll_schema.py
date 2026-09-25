import time
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def poll_schema():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    server_params = StdioServerParameters(command="tigergraph-mcp", args=[], env=os.environ.copy())
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            for _ in range(10): # try 10 times, wait 5s each
                try:
                    res = await session.call_tool("tigergraph__get_graph_schema", {"graph_name": "Transaction_Fraud"})
                    text = res.content[0].text
                    if "Internal Server Error" not in text and "success\": false" not in text:
                        print("Schema fetched successfully!")
                        with open('schema_live.json', 'w', encoding='utf-8') as f:
                            f.write(text)
                        return
                    else:
                        print("Server still returning error, waiting 5s...")
                except Exception as e:
                    print(f"Exception: {e}")
                
                time.sleep(5)
            print("Timed out waiting for server to be ready.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(poll_schema())
