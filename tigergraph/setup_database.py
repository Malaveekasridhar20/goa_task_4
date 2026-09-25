import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    import pyTigerGraph as tg
except ImportError:
    print("BLOCKED: pyTigerGraph is not installed in this environment.")
    sys.exit(1)

def setup():
    host = os.environ.get("TG_HOST")
    graph = os.environ.get("TG_GRAPHNAME")
    user = os.environ.get("TG_USERNAME", "tigergraph")
    pw = os.environ.get("TG_PASSWORD", "tigergraph")
    secret = os.environ.get("TG_SECRET")
    
    if not host or not graph:
        print("BLOCKED: Missing TigerGraph credentials (TG_HOST, TG_GRAPHNAME)")
        sys.exit(1)
        
    print(f"Connecting to TigerGraph at {host} for graph {graph}...")
    try:
        if secret:
            conn = tg.TigerGraphConnection(host=host, graphname=graph, gsqlSecret=secret)
            conn.apiToken = conn.getToken(secret)[0]
        else:
            conn = tg.TigerGraphConnection(host=host, graphname=graph, username=user, password=pw)
            conn.apiToken = conn.getToken(conn.createSecret())
        
        print("Installing schema...")
        try:
            with open("tigergraph/schema.gsql", "r") as f:
                res = conn.gsql(f"USE GRAPH {graph}\n" + f.read())
                print(res)
        except Exception as e:
            print("Schema installation message:", e)
            
        print("Installing queries...")
        try:
            with open("tigergraph/queries.gsql", "r") as f:
                queries_sql = f.read().replace("FraudGraph", graph)
                # First create the queries
                res = conn.gsql(f"USE GRAPH {graph}\n" + queries_sql)
                print(res)
            # Then install them
            res2 = conn.gsql(f"USE GRAPH {graph}\nINSTALL QUERY ALL")
            print(res2)
        except Exception as e:
            print("Query installation message:", e)
            
        print("Success! Schema and queries installed.")
    except Exception as e:
        print(f"FAILED to connect or install: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup()
