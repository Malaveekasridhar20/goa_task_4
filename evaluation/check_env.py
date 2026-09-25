import os
from dotenv import load_dotenv

load_dotenv()

print("--- CREDENTIALS CHECK ---")
print(f"TG_HOST present: {'Yes' if os.environ.get('TG_HOST') else 'No'}")
print(f"TG_GRAPHNAME present: {'Yes' if os.environ.get('TG_GRAPHNAME') else 'No'}")
print(f"TG_SECRET present: {'Yes' if os.environ.get('TG_SECRET') else 'No'}")
print(f"DEMO_MODE: {os.environ.get('DEMO_MODE')}")
print("-------------------------")
