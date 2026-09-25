import json
import re

transcript_path = r"C:\Users\malav\.gemini\antigravity-ide\brain\1f5577bb-d28f-45f5-925b-2005c6eef341\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Let's search for "vertex_type_count": 18
# and capture backwards to { and forwards to } to get the json.
match = re.search(r'(\{"GraphName".*?"vertex_type_count":\s*18,\s*"edge_type_count":\s*22\s*\})', text, re.DOTALL | re.IGNORECASE)
if match:
    with open('scratch_schema.json', 'w', encoding='utf-8') as out:
        out.write(match.group(1))
    print("Successfully extracted schema from raw string match!")
else:
    # Try another regex
    match2 = re.search(r'(\{"GraphName".*?"vertex_type_count".*?\})', text, re.DOTALL | re.IGNORECASE)
    if match2:
        with open('scratch_schema.json', 'w', encoding='utf-8') as out:
            out.write(match2.group(1))
        print("Successfully extracted schema from fallback regex!")
    else:
        print("Still not found!")
