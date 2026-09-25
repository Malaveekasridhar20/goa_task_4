import json

class GraphInvestigationTools:
    def _clean_json(self, text):
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def test(self):
        edge_res = """```json
{
  "success": true,
  "operation": "get_node_edges",
  "data": {
    "edges": [
      {
        "e_type": "Merchant_Receive_Transaction",
        "directed": false,
        "from_id": "5298",
        "from_type": "Payment_Transaction",
        "to_id": "fraud_Erdman-Kertzmann",
        "to_type": "Merchant",
        "attributes": {}
      },
      {
        "e_type": "Card_Send_Transaction",
        "directed": false,
        "from_id": "5298",
        "from_type": "Payment_Transaction",
        "to_id": "4602925468627288",
        "to_type": "Card",
        "attributes": {}
      }
    ]
  }
}
```"""
        try:
            edges = json.loads(self._clean_json(edge_res)).get("data", {}).get("edges", [])
            print("edges:", edges)
            card_id = None
            for edge in edges:
                if edge.get("e_type") == "Card_Send_Transaction" or edge.get("e_type") == "reverse_Card_Send_Transaction" or edge.get("to_type") == "Card":
                    card_id = edge.get("to_id")
                elif edge.get("from_type") == "Card":
                    card_id = edge.get("from_id")
            print("card_id:", card_id)
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    tools = GraphInvestigationTools()
    tools.test()
