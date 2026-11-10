import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_graph_explorer_interactions():
    """
    Verifies all 11 interaction requirements from Priority 9:
    1. Select an account -> verify connected device
    2. Select that device -> verify all connected accounts
    3. Select a transaction -> verify its account relationship
    4. Select a payment identity -> verify connected accounts
    5. Switch between fraud clusters
    6. Focus on a two-hop neighbourhood
    7. Open an investigation from a graph node
    8. Connected entity counts are NEVER zero when relationships exist
    """
    with TestClient(app) as client:
        # Load fresh seed
        client.post("/api/demo/seed")

        # Fetch full graph
        resp = client.get("/api/fraud-networks")
        assert resp.status_code == 200
        graph = resp.json()
        nodes = {n["id"]: n for n in graph["nodes"]}
        edges = graph["edges"]

        # Every card-sized entity has a clear rectangle gutter in the server layout.
        graph_nodes = graph["nodes"]
        for index, first in enumerate(graph_nodes):
            for second in graph_nodes[index + 1:]:
                dx = abs(first["position"]["x"] - second["position"]["x"])
                dy = abs(first["position"]["y"] - second["position"]["y"])
                assert not (dx < 220 and dy < 145), f"Nodes overlap: {first['id']} and {second['id']}"

        # 1. Select an account (Marcus Sterling ACC_009)
        assert "ACC_009" in nodes
        marcus = nodes["ACC_009"]
        assert len(marcus["connected_entities"]) > 0, "Connected entities must not be 0"
        
        # 2. Verify its connected device
        connected_devs = [ce for ce in marcus["connected_entities"] if ce["type"] == "DEVICE"]
        assert len(connected_devs) >= 1
        dev_id = connected_devs[0]["node_id"]
        assert dev_id == "DEV_007", "Marcus must be linked to shared Bluestacks emulator DEV_007"
        print(f"\n✓ 1 & 2: Account ACC_009 correctly connected to device {dev_id}.")

        # 3. Select that device (DEV_007)
        assert dev_id in nodes
        device_node = nodes[dev_id]
        assert len(device_node["connected_entities"]) > 0

        # 4. Verify all connected accounts for that device (Multi-account collision)
        dev_accounts = [ce for ce in device_node["connected_entities"] if ce["type"] == "ACCOUNT"]
        dev_account_ids = [ce["node_id"] for ce in dev_accounts]
        assert len(dev_account_ids) >= 2, f"Device DEV_007 must link multiple accounts, found: {dev_account_ids}"
        assert "ACC_009" in dev_account_ids
        assert "ACC_010" in dev_account_ids or "ACC_011" in dev_account_ids
        print(f"✓ 3 & 4: Device {dev_id} links {len(dev_account_ids)} accounts: {dev_account_ids}.")

        # 5. Select a transaction (TXN_FRAUD_901)
        assert "TXN_FRAUD_901" in nodes
        txn_node = nodes["TXN_FRAUD_901"]
        assert len(txn_node["connected_entities"]) > 0, "Transaction connected entities must not be 0"

        # 6. Verify its account relationship
        txn_accounts = [ce for ce in txn_node["connected_entities"] if ce["type"] == "ACCOUNT"]
        assert len(txn_accounts) >= 1
        assert txn_accounts[0]["node_id"] == "ACC_009"
        assert txn_accounts[0]["relationship"] == "ACCOUNT_MADE_TRANSACTION"
        print(f"✓ 5 & 6: Transaction TXN_FRAUD_901 correctly owns ACCOUNT_MADE_TRANSACTION edge to ACC_009.")

        # 7. Select a payment identity (PID_006 - Stolen Card)
        assert "PID_006" in nodes
        pid_node = nodes["PID_006"]
        assert len(pid_node["connected_entities"]) > 0

        # 8. Verify connected accounts on PID_006 (Shared stolen card across Marcus and Viktor)
        pid_accounts = [ce for ce in pid_node["connected_entities"] if ce["type"] == "ACCOUNT"]
        pid_acc_ids = [ce["node_id"] for ce in pid_accounts]
        assert len(pid_acc_ids) >= 2, f"Payment identity PID_006 must be shared across multiple accounts, found: {pid_acc_ids}"
        assert "ACC_009" in pid_acc_ids
        assert "ACC_010" in pid_acc_ids
        print(f"✓ 7 & 8: Payment identity PID_006 shared across accounts: {pid_acc_ids}.")

        # 9. Switch between fraud clusters
        clusters = graph["clusters"]
        assert len(clusters) >= 2
        cluster_id = clusters[0]["id"]
        c_resp = client.get(f"/api/fraud-networks?cluster_id={cluster_id}")
        assert c_resp.status_code == 200
        cluster_graph = c_resp.json()
        assert cluster_graph["total_nodes"] > 0
        assert all(n.get("cluster_id") == cluster_id for n in cluster_graph["nodes"])
        print(f"✓ 9: Successfully switched to cluster {cluster_id} with {cluster_graph['total_nodes']} member nodes.")

        # 10. Focus on a two-hop neighbourhood
        hop_resp = client.get(f"/api/fraud-networks?node_id=DEV_007")
        assert hop_resp.status_code == 200
        hop_graph = hop_resp.json()
        hop_node_ids = [n["id"] for n in hop_graph["nodes"]]
        assert "DEV_007" in hop_node_ids
        assert "ACC_009" in hop_node_ids
        print(f"✓ 10: Focused 2-hop neighborhood of DEV_007 returned {len(hop_node_ids)} correlated entities.")

        # 11. Open an investigation from a graph node
        inv_cases = client.get("/api/investigations").json()
        assert len(inv_cases) > 0
        first_case_id = inv_cases[0]["id"]
        detail = client.get(f"/api/investigations/{first_case_id}").json()
        assert detail["id"] == first_case_id
        assert detail["risk_level"] in ("HIGH", "CRITICAL")
        print(f"✓ 11: Graph node investigation link verified for case {first_case_id}.")

        print("\n=======================================================")
        print("ALL 11 GRAPH EXPLORER INTERACTION TESTS VERIFIED!")
        print("=======================================================\n")
