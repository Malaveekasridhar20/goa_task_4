import json
import os
import io

def generate():
    with io.open('schema_utf8.json', 'r', encoding='utf-8') as f:
        text = f.read()
        import re
        match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
        if match:
            text = match.group(1)
        data = json.loads(text)
            
    schema = data.get('results', [{}])[0]
    
    vertices = schema.get('VertexTypes', [])
    edges = schema.get('EdgeTypes', [])
    
    os.makedirs('docs', exist_ok=True)
    with open('docs/actual_graph_inventory.md', 'w', encoding='utf-8') as f:
        f.write("# Actual Graph Inventory\n\n")
        f.write("This document reflects the exact native schema of the `Transaction_Fraud` graph in TigerGraph.\n\n")
        
        f.write(f"## 1. Vertices ({len(vertices)})\n\n")
        for v in vertices:
            f.write(f"### `{v['Name']}`\n")
            primary_id = v.get('PrimaryId', {})
            f.write(f"- **Primary ID**: `{primary_id.get('AttributeName')}` ({primary_id.get('AttributeType', {}).get('Name')})\n")
            attrs = v.get('Attributes', [])
            if attrs:
                f.write("- **Attributes**:\n")
                for a in attrs:
                    f.write(f"  - `{a.get('AttributeName')}` ({a.get('AttributeType', {}).get('Name')})\n")
            else:
                f.write("- **Attributes**: None\n")
            f.write("\n")
            
        f.write(f"## 2. Edges ({len(edges)})\n\n")
        for e in edges:
            f.write(f"### `{e['Name']}`\n")
            f.write(f"- **Directed**: {e.get('IsDirected')}\n")
            
            pairs = e.get('EdgePairs', [])
            if not pairs:
                f.write(f"- **From**: `{e.get('FromVertexTypeName')}` → **To**: `{e.get('ToVertexTypeName')}`\n")
            else:
                f.write("- **Allowed Pairs (Polymorphic)**:\n")
                for p in pairs:
                    f.write(f"  - `{p['From']}` → `{p['To']}`\n")
                    
            attrs = e.get('Attributes', [])
            if attrs:
                f.write("- **Attributes**:\n")
                for a in attrs:
                    f.write(f"  - `{a.get('AttributeName')}` ({a.get('AttributeType', {}).get('Name')})\n")
            else:
                f.write("- **Attributes**: None\n")
            f.write("\n")

        # Now append the Traversal Map requested
        f.write("## 3. Fraud Investigation Traversal Map\n\n")
        f.write("### Payment_Transaction → Card → related transactions\n")
        f.write("Signal: Identifies if the same card was used in other fraudulent or high-risk transactions. High velocity of transactions on one card in a short period suggests account takeover or card testing.\n\n")
        
        f.write("### Payment_Transaction → Merchant → Merchant_Category\n")
        f.write("Signal: Reveals if the transaction is directed at high-risk merchant categories (e.g., gambling, electronics) which are often targeted by fraudsters.\n\n")
        
        f.write("### Payment_Transaction → Card → Party → Device\n")
        f.write("Signal: Connects the transaction to the device used. If the device is new, unseen, or associated with multiple different parties/cards, it strongly suggests a fraudulent device or bot network.\n\n")

        f.write("### Payment_Transaction → Card → Party → IP\n")
        f.write("Signal: Connects the transaction to an IP address. Multiple transactions from different cards coming from the same IP (or high-risk IPs) signal coordinated fraud or account takeover.\n\n")
        
        f.write("### Payment_Transaction → Card → Party → Address → Zipcode → City → State\n")
        f.write("Signal: Provides the geographical location of the party. If the transaction occurs far from this established address (out-of-region), it signals potential card-present fraud or stolen details.\n\n")

        f.write("### Card → Community\n")
        f.write("Signal: Identifies if the card belongs to a known fraudulent community or ring (detected via graph algorithms like Louvain). Highlights organized fraud.\n\n")

        f.write("### Merchant → Community\n")
        f.write("Signal: Shows if the merchant is part of a high-risk cluster (e.g., a group of colluding merchants processing fake transactions).\n\n")

        f.write("### Party → Community\n")
        f.write("Signal: Flags individuals who are tightly connected to known fraudsters in a community, acting as mules or accomplices.\n\n")

        f.write("### Card → Merchant\n")
        f.write("Signal: Analyzes the direct relationship frequency. A sudden spike in activity between a specific card and a specific merchant can indicate collusion or a targeted attack.\n\n")

        f.write("### Merchant → Merchant\n")
        f.write("Signal: Identifies related merchants (e.g., sharing terminals, owners, or transaction patterns). Useful for uncovering larger fraud rings masking as independent businesses.\n\n")
        
if __name__ == '__main__':
    generate()
