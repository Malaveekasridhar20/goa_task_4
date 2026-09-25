import json
import os
import asyncio
import pandas as pd
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()

def clean_json(text):
    text = text.strip()
    import re
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Otherwise just find the first balanced JSON object
    try:
        import json
        for line in text.split('\n'):
            if line.startswith('{'):
                return line
    except:
        pass
    start = text.find('{')
    if start != -1:
        # Find the end of this block
        stack = []
        for i in range(start, len(text)):
            if text[i] == '{': stack.append('{')
            elif text[i] == '}': 
                stack.pop()
                if not stack:
                    return text[start:i+1]
    return text.strip()

async def create_mapped_pack():
    server_params = StdioServerParameters(command='tigergraph-mcp', args=[], env=os.environ.copy())
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("Fetching 20 transactions from TigerGraph...")
            res = await session.call_tool('tigergraph__get_nodes', {
                'graph_name': 'Transaction_Fraud', 
                'vertex_type': 'Payment_Transaction', 
                'limit': 20
            })
            
            try:
                data = json.loads(clean_json(res.content[0].text))
                txns = data.get("data", {}).get("vertices", [])
            except Exception as e:
                print("Failed to parse nodes:", e)
                return
                
            if not txns:
                print("No transactions found in TigerGraph!")
                return
                
            print(f"Found {len(txns)} transactions.")
            
            # Read original pack
            df = pd.read_csv('C:/Users/malav/Downloads/case_pack.csv')
            
            mapped_rows = []
            
            for i, row in df.iterrows():
                if i < len(txns):
                    tg_txn_id = txns[i].get("v_id")
                    
                    # Also try to find a card ID for the transaction
                    edge_res = await session.call_tool('tigergraph__get_node_edges', {
                        'vertex_type': 'Payment_Transaction',
                        'vertex_id': tg_txn_id
                    })
                    
                    card_id = "UNKNOWN"
                    try:
                        edges_data = json.loads(clean_json(edge_res.content[0].text))
                        edges = edges_data.get("data", {}).get("edges", [])
                        for e in edges:
                            if e.get("to_type") == "Card":
                                card_id = e.get("to_id")
                                break
                    except:
                        pass
                        
                    mapped_row = row.copy()
                    mapped_row["original_flagged_txn_id"] = row["flagged_txn_id"]
                    mapped_row["flagged_txn_id"] = tg_txn_id
                    mapped_row["original_card_id"] = row["card_id"]
                    mapped_row["card_id"] = card_id
                    mapped_row["mapping_method"] = "DEMO_MAPPING"
                    mapped_row["mapping_confidence"] = "0%"
                    mapped_row["is_officially_supported"] = "False"
                    
                    mapped_rows.append(mapped_row)
                    
            mapped_df = pd.DataFrame(mapped_rows)
            mapped_df.to_csv("evaluation/case_pack_mapped.csv", index=False)
            print("Saved mapped benchmark to evaluation/case_pack_mapped.csv")

if __name__ == "__main__":
    asyncio.run(create_mapped_pack())
