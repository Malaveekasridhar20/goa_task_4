import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Try to import pyTigerGraph, handle gracefully if not installed yet
try:
    import pyTigerGraph as tg
except ImportError:
    tg = None

load_dotenv()

TIGERGRAPH_HOST = os.getenv("TIGERGRAPH_HOST")
TIGERGRAPH_USERNAME = os.getenv("TIGERGRAPH_USERNAME")
TIGERGRAPH_PASSWORD = os.getenv("TIGERGRAPH_PASSWORD")
TIGERGRAPH_GRAPH = os.getenv("TIGERGRAPH_GRAPH", "FraudGraph")

def get_tg_connection():
    if not TIGERGRAPH_HOST or not TIGERGRAPH_USERNAME or not TIGERGRAPH_PASSWORD:
        print("ERROR: Missing TigerGraph credentials. Ensure TIGERGRAPH_HOST, TIGERGRAPH_USERNAME, and TIGERGRAPH_PASSWORD are set in .env")
        return None
        
    try:
        conn = tg.TigerGraphConnection(
            host=TIGERGRAPH_HOST,
            username=TIGERGRAPH_USERNAME,
            password=TIGERGRAPH_PASSWORD,
            graphname=TIGERGRAPH_GRAPH
        )
        conn.apiToken = conn.getToken(conn.createSecret())
        return conn
    except Exception as e:
        print(f"Failed to connect to TigerGraph: {e}")
        return None

def load_data():
    conn = get_tg_connection()
    if not conn:
        print("Skipping real data load. Local mock adapter will be used for UI development.")
        return

    print("Connected to TigerGraph. Loading data...")

    # Define paths
    base_dir = r"c:\Users\malav\Downloads"
    transactions_path = os.path.join(base_dir, "transactions.csv")
    identity_path = os.path.join(base_dir, "identity.csv")
    closed_cases_path = os.path.join(base_dir, "closed_cases_history.csv")

    try:
        print("Loading transactions.csv ...")
        # Optimization: chunking can be used for large files
        df_tx = pd.read_csv(transactions_path)
        
        # Load Customers
        customers = df_tx[['customer_id']].drop_duplicates().dropna()
        conn.upsertVertexDataFrame(df=customers, vertexType='Customer', v_id='customer_id')
        
        # Load Cards
        cards = df_tx[['card1', 'card4', 'card6', 'card1', 'card2', 'card3', 'card5']].copy()
        # In this dataset, card_id is not explicitly formed like 'C01234-K1' except in case pack and closed cases. 
        # But we know `customer_id` and card features exist. The instructions say "Card IDs in the cases look like C01234-K1"
        # Since we don't have explicit card_ids in transactions, we derive them or rely on customer_id. 
        # Actually, let's load transactions first.
        
        tx_cols = ['TransactionID', 'ts', 'TransactionAmt', 'ProductCD', 'channel', 'risk_score']
        transactions = df_tx[tx_cols].dropna(subset=['TransactionID'])
        conn.upsertVertexDataFrame(df=transactions, vertexType='Transaction', v_id='TransactionID', attributes={'ts': 'ts', 'amount': 'TransactionAmt', 'product_cd': 'ProductCD', 'channel': 'channel', 'risk_score': 'risk_score'})
        
        print("Transactions loaded successfully.")
    except Exception as e:
        print(f"Error loading transactions: {e}")

    try:
        print("Loading identity.csv ...")
        df_id = pd.read_csv(identity_path)
        # DeviceProfile 
        devices = df_id[['TransactionID', 'DeviceInfo', 'DeviceType', 'id_30', 'id_31', 'id_33', 'id_34', 'id_23']].copy()
        # Map device profile ID (a hash or unique combination)
        devices['device_id'] = devices['DeviceInfo'].fillna('Unknown') + '|' + devices['id_30'].fillna('Unknown') + '|' + devices['id_31'].fillna('Unknown')
        devices_unique = devices[['device_id', 'DeviceType', 'DeviceInfo', 'id_30', 'id_31', 'id_33', 'id_34', 'id_23']].drop_duplicates()
        
        conn.upsertVertexDataFrame(df=devices_unique, vertexType='DeviceProfile', v_id='device_id', attributes={'device_type': 'DeviceType', 'device_info': 'DeviceInfo', 'os': 'id_30', 'browser': 'id_31', 'screen': 'id_33', 'match_status': 'id_34', 'proxy_rating': 'id_23'})
        
        # FROM_DEVICE Edge
        edge_from_device = devices[['TransactionID', 'device_id']].dropna()
        conn.upsertEdgeDataFrame(df=edge_from_device, sourceVertexType='Transaction', edgeType='FROM_DEVICE', targetVertexType='DeviceProfile', from_id='TransactionID', to_id='device_id')
        print("Identity data loaded successfully.")
    except Exception as e:
        print(f"Error loading identity: {e}")

if __name__ == "__main__":
    load_data()
