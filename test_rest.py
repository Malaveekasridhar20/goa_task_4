import os
import requests
from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

host = os.environ.get("TG_HOST")
graph = os.environ.get("TG_GRAPHNAME")
user = os.environ.get("TG_USERNAME")
pw = os.environ.get("TG_PASSWORD")

try:
    url = f"{host}/restpp/builtins/{graph}"
    payload = {"function":"stat_vertex_number","type":"*"}
    resp = requests.post(url, json=payload, auth=(user, pw), verify=False)
    print("Vertex Counts:", resp.json())
    
    # Try fetching one transaction
    url2 = f"{host}/restpp/graph/{graph}/vertices/Payment_Transaction?limit=2"
    resp2 = requests.get(url2, auth=(user, pw), verify=False)
    print("Vertices Sample:", resp2.json())
except Exception as e:
    print("Error:", e)
