import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.mcp_client import MCPClient

def test_mcp_integration():
    print("Testing Native TigerGraph MCP Integration...")
    server_script = os.path.join("tigergraph", "mcp", "server.py")
    
    client = MCPClient(server_script)
    print("Starting client and completing handshake...")
    init_res = client.start()
    print("Handshake Response:", init_res)
    
    print("\nListing Tools...")
    tools_res = client.list_tools()
    print("Tools:", [t["name"] for t in tools_res["result"]["tools"]])
    
    assert len(tools_res["result"]["tools"]) >= 3, "Failed to load tools via MCP"
    
    print("\nInvoking Tool: get_transaction_context...")
    call_res = client.call_tool("get_transaction_context", {"txn_id": "3514030"})
    print("Call Result:", call_res)
    
    assert "REAL MCP PROTOCOL" in call_res, "Failed to execute tool via MCP"
    
    print("\nInvoking Tool: find_shared_devices...")
    call_res = client.call_tool("find_shared_devices", {"txn_id": "3514030"})
    print("Call Result:", call_res)
    
    client.stop()
    print("\nMCP Integration Test Passed Successfully!")

if __name__ == "__main__":
    test_mcp_integration()
