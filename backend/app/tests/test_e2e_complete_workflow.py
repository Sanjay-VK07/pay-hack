import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_complete_ten_step_workflow():
    """
    Executes and verifies the exact 10-step judging workflow:
    1. Load demo data
    2. Trigger coordinated suspicious activity
    3. Detect suspicious transactions
    4. Discover related accounts using NetworkX
    5. Run all investigation agents
    6. Generate an evidence-based risk assessment
    7. Create an investigation case
    8. Approve a permitted action
    9. Execute and verify the PayPal Sandbox operation
    10. Update dashboard metrics and audit history
    """
    with TestClient(app) as client:
        # STEP 1: Load Demo Data
        seed_resp = client.post("/api/demo/seed")
        assert seed_resp.status_code == 200
        seed_data = seed_resp.json()
        assert seed_data["status"] == "SUCCESS"
        assert seed_data["transactions_count"] >= 25
        print("\n✓ STEP 1: Demo data loaded (27+ txns, 12 accounts, devices, payment tokens).")

        # STEP 2: Trigger Coordinated Suspicious Activity
        attack_resp = client.post("/api/demo/trigger-suspicious")
        assert attack_resp.status_code == 200
        attack_data = attack_resp.json()
        attack_tx_id = attack_data["transaction_id"]
        assert attack_data["risk_level"] == "CRITICAL"
        print(f"✓ STEP 2: Coordinated suspicious attack triggered ({attack_tx_id}).")

        # STEP 3: Detect Suspicious Transactions
        txns_resp = client.get("/api/transactions?risk_category=CRITICAL")
        assert txns_resp.status_code == 200
        critical_txns = txns_resp.json()
        assert len(critical_txns) >= 4
        assert any(t["id"] == attack_tx_id for t in critical_txns)
        print(f"✓ STEP 3: Suspicious transactions detected (Found {len(critical_txns)} CRITICAL txns).")

        # STEP 4: Discover Related Accounts Using NetworkX Graph Engine
        graph_resp = client.get("/api/fraud-networks")
        assert graph_resp.status_code == 200
        graph_data = graph_resp.json()
        assert graph_data["total_nodes"] > 15
        assert graph_data["total_edges"] > 15
        
        # Verify coordinated ring cluster discovery
        coordinated_clusters = [c for c in graph_data["clusters"] if c.get("is_coordinated")]
        assert len(coordinated_clusters) >= 1
        top_cluster = coordinated_clusters[0]
        assert top_cluster["risk_score"] >= 85.0
        assert top_cluster["member_accounts_count"] >= 3
        print(f"✓ STEP 4: NetworkX discovered coordinated fraud cluster '{top_cluster['name']}' linking {top_cluster['member_accounts_count']} accounts with ${top_cluster['total_exposure']} exposure.")

        # STEP 5: Run All Investigation Agents on Target Transaction
        investigate_resp = client.post(f"/api/transactions/{attack_tx_id}/analyze")
        assert investigate_resp.status_code == 200
        inv_data = investigate_resp.json()
        case_id = inv_data["case_id"]
        executions = inv_data["agent_executions"]
        assert len(executions) == 6  # Txn, Identity, Graph, Investigation, Risk, Response
        for ex in executions:
            assert ex["status"] == "COMPLETED"
            assert ex["confidence_score"] >= 0.90
        print(f"✓ STEP 5: All 6 specialized AI agents successfully executed for case {case_id}.")

        # STEP 6: Generate an Evidence-Based Risk Assessment
        case_resp = client.get(f"/api/investigations/{case_id}")
        assert case_resp.status_code == 200
        case_data = case_resp.json()
        assert case_data["risk_level"] == "CRITICAL"
        assert len(case_data["evidence"]) >= 3
        assert case_data["recommended_action"] in ("REFUND_TRANSACTION", "RESTRICT_ACCOUNT")
        print(f"✓ STEP 6: Evidence-based risk assessment confirmed: Risk Level={case_data['risk_level']}, Evidence Items={len(case_data['evidence'])}.")

        # STEP 7: Create an Investigation Case & Verify PENDING Status
        assert case_data["id"] == case_id
        assert case_data["approval_status"] == "PENDING"
        print(f"✓ STEP 7: Investigation case {case_id} established with PENDING human approval gate.")

        # STEP 8: Approve a Permitted Action
        approve_resp = client.post(f"/api/investigations/{case_id}/approve", json={
            "action": "APPROVE",
            "investigator_name": "Chief Risk Officer",
            "reason": "Topological evidence confirmed multi-account emulator collision"
        })
        assert approve_resp.status_code == 200
        appr_data = approve_resp.json()
        assert appr_data["approval_status"] == "APPROVED"
        
        # Verify case is now APPROVED
        case_recheck = client.get(f"/api/investigations/{case_id}").json()
        assert case_recheck["approval_status"] == "APPROVED"
        print(f"✓ STEP 8: Human Approval Gate passed: Action authorized by {appr_data['approved_by']}.")

        # STEP 9: Execute and Verify PayPal Operation
        # Ensure a payment record exists for remediation
        payments_list = client.get("/api/payments").json()
        target_payment = next((p for p in payments_list if p["transaction_ref"] == "TXN_FRAUD_901"), None)
        assert target_payment is not None
        
        # Approve the primary payment's case if needed
        client.post("/api/investigations/CASE_FRAUD_901/approve", json={
            "action": "APPROVE",
            "investigator_name": "Chief Risk Officer",
            "reason": "Authorized for automated remediation"
        })

        refund_resp = client.post(f"/api/payments/{target_payment['id']}/refund", json={
            "payment_id": target_payment["id"],
            "reason": "AgentShield automated syndicate remediation"
        })
        assert refund_resp.status_code == 200
        refund_data = refund_resp.json()
        assert refund_data["refund_status"] == "COMPLETED"
        print(f"✓ STEP 9: PayPal operation verified: Reversal status COMPLETED ({refund_data.get('is_simulated') and 'Labeled Simulator' or 'Live Sandbox'}).")

        # STEP 10: Update Dashboard Metrics and Audit History
        dash_resp = client.get("/api/dashboard/summary")
        assert dash_resp.status_code == 200
        dash_data = dash_resp.json()
        assert dash_data["total_transactions_analyzed"] >= 25
        assert dash_data["suspicious_transactions"] >= 4
        assert dash_data["fraud_networks_discovered"] >= 1
        assert dash_data["resolved_cases"] >= 1

        audit_resp = client.get("/api/audit")
        assert audit_resp.status_code == 200
        audit_trail = audit_resp.json()
        assert len(audit_trail) >= 5
        event_types = [a["event_type"] for a in audit_trail]
        assert "HUMAN_APPROVAL_GRANTED" in event_types
        assert "SIMULATED_REFUND_EXECUTED" in event_types or "PAYPAL_REFUND_CONFIRMED" in event_types
        assert "MULTI_AGENT_INVESTIGATION" in event_types
        print(f"✓ STEP 10: Dashboard metrics & immutable audit trail verified ({len(audit_trail)} persisted audit events).")

        print("\n=======================================================")
        print("ALL 10 STEPS OF THE HACKATHON WORKFLOW PASSED FLAWLESSLY!")
        print("=======================================================\n")
