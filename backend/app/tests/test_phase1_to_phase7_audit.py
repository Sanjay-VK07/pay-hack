import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_fifteen_step_fraud_investigation_and_safety_scenario(client):
    """
    PHASE 7: Full 15-Step Master Integration Scenario:
    1. Seed demo transactions.
    2. Trigger coordinated fraudulent activity.
    3. Detect suspicious transactions.
    4. Build the NetworkX relationship graph.
    5. Discover connected fraud accounts.
    6. Execute the six investigation agents.
    7. Generate evidence-backed risk assessment.
    8. Create an investigation case.
    9. Request human approval.
    10. Approve the case.
    11. Verify the actual PayPal Sandbox capture.
    12. Execute the actual Sandbox refund.
    13. Verify the refund response.
    14. Update the case.
    15. Record every event in the audit trail.
    """
    # STEP 1: Seed demo transactions
    seed_resp = client.post("/api/demo/seed")
    assert seed_resp.status_code == 200
    assert seed_resp.json()["status"] == "SUCCESS"

    # STEP 2: Trigger coordinated fraudulent activity
    attack_resp = client.post("/api/demo/trigger-suspicious")
    assert attack_resp.status_code == 200
    attack_data = attack_resp.json()
    assert attack_data["status"] == "SUCCESS"
    target_txn_id = attack_data["transaction_id"]
    assert target_txn_id == "TXN_ATTACK_999"

    # STEP 3: Detect suspicious transactions
    txn_resp = client.get(f"/api/transactions/{target_txn_id}")
    assert txn_resp.status_code == 200
    txn_data = txn_resp.json()
    assert txn_data["risk_category"] in ("HIGH", "CRITICAL")
    assert txn_data["amount"] == 2890.00

    # STEP 4: Build the NetworkX relationship graph
    graph_resp = client.get("/api/fraud-networks")
    assert graph_resp.status_code == 200
    graph_data = graph_resp.json()
    assert graph_data["total_nodes"] > 10
    assert graph_data["total_edges"] > 10

    # STEP 5: Discover connected fraud accounts
    clusters = graph_data["clusters"]
    assert len(clusters) > 0
    coordinated_clusters = [c for c in clusters if c.get("is_coordinated")]
    assert len(coordinated_clusters) > 0
    top_cluster = coordinated_clusters[0]
    assert len(top_cluster["account_ids"]) >= 3

    # STEP 6: Execute the six investigation agents
    inv_run_resp = client.post(f"/api/transactions/{target_txn_id}/analyze")
    assert inv_run_resp.status_code == 200
    inv_run_data = inv_run_resp.json()
    case_id = inv_run_data["case_id"]

    # Verify all 6 agents were executed
    case_detail_resp = client.get(f"/api/investigations/{case_id}")
    assert case_detail_resp.status_code == 200
    case_detail = case_detail_resp.json()
    executions = case_detail.get("agent_executions", [])
    assert len(executions) == 6, f"Expected 6 agents, found {len(executions)}"

    agent_names = [e["agent_name"] for e in executions]
    expected_agents = [
        "Transaction Intelligence Agent",
        "Identity Intelligence Agent",
        "Graph Intelligence Agent",
        "Fraud Investigation Agent",
        "Risk Assessment Agent",
        "Response Planning Agent"
    ]
    for expected in expected_agents:
        assert expected in agent_names, f"Missing agent: {expected}"

    # Verify structured outputs and execution durations
    for e in executions:
        assert e["execution_time_ms"] > 0
        assert e["status"] == "COMPLETED"
        assert e.get("confidence_score") is None
        assert e["findings"] is not None

    # STEP 7: Generate evidence-backed risk assessment
    risk_assessments = case_detail.get("risk_assessments", [])
    assert len(risk_assessments) > 0
    ra = risk_assessments[0]
    assert ra["risk_score"] >= 85.0
    assert ra["risk_level"] == "CRITICAL"
    assert len(ra["evidence_ids"]) >= 3
    assert len(case_detail["evidence"]) >= 3

    # STEP 8: Create an investigation case (validated above as case_id)
    assert case_detail["id"] == case_id
    assert case_detail["status"] == "PENDING_REVIEW"
    assert case_detail["approval_status"] == "PENDING"
    assert case_detail["recommended_action"] == "REFUND_TRANSACTION"

    # STEP 9: Request human approval (verify approval request exists)
    approval_requests = case_detail.get("approval_requests", [])
    assert len(approval_requests) > 0
    assert approval_requests[0]["status"] == "PENDING"

    # STEP 10: Approve the case
    approve_resp = client.post(f"/api/investigations/{case_id}/approve", json={
        "action": "APPROVE",
        "investigator_name": "Chief Security Officer",
        "reason": "Authorized refund reversal based on multi-agent graph corroboration"
    })
    assert approve_resp.status_code == 200
    app_data = approve_resp.json()
    assert app_data["status"] == "SUCCESS"
    assert app_data["approval_status"] == "APPROVED"
    assert "operation_reference" in app_data

    # STEP 11: Verify the actual PayPal Sandbox capture
    verify_resp = client.get(f"/api/payments/{case_id}/verify")
    assert verify_resp.status_code == 200
    vdata = verify_resp.json()
    capture_id = vdata["capture_id"]
    assert capture_id is not None
    assert vdata["captured_amount"] > 0
    assert vdata["refundable_balance"] > 0
    assert vdata["integration_mode"] in ("LIVE_PAYPAL_SANDBOX", "SIMULATED_SANDBOX")

    # STEP 12: Execute the actual Sandbox refund
    payment_id = vdata["payment_id"]
    refund_resp = client.post(f"/api/payments/{payment_id}/refund", json={
        "amount": vdata["refundable_balance"],
        "reason": "AgentShield fraudulent transaction mitigation",
        "investigator": "Chief Security Officer"
    })
    assert refund_resp.status_code == 200
    ref_data = refund_resp.json()
    assert ref_data["status"] == "SUCCESS"
    assert ref_data["refund_status"] == "COMPLETED"
    assert "paypal_reference" in ref_data

    # STEP 13: Verify the refund response
    post_refund_verify = client.get(f"/api/payments/{payment_id}/verify").json()
    assert post_refund_verify["refundable_balance"] == 0.0
    assert post_refund_verify["has_previous_refund"] is True
    assert len(post_refund_verify["previous_refunds"]) > 0

    # STEP 14: Update the case
    updated_case = client.get(f"/api/investigations/{case_id}").json()
    assert updated_case["status"] in ("ACTION_COMPLETED", "APPROVED")

    # STEP 15: Record every event in the audit trail
    audit_resp = client.get(f"/api/audit?case_id={case_id}")
    assert audit_resp.status_code == 200
    audit_logs = audit_resp.json()
    assert len(audit_logs) >= 3

    event_types = [l["event_type"] for l in audit_logs]
    assert "HUMAN_APPROVAL_GRANTED" in event_types
    assert "SIMULATED_REFUND_EXECUTED" in event_types or "PAYPAL_REFUND_CONFIRMED" in event_types

def test_financial_safety_edge_cases(client):
    """
    Test edge cases:
    - Rejected approvals cannot execute refunds
    - Missing captures cannot execute refunds
    - Duplicate refunds return idempotent response
    - Invalid refund amount triggers 400 validation
    """
    # 1. Rejected Case
    client.post("/api/demo/seed")
    cases = client.get("/api/investigations").json()
    pending_case = next(c for c in cases if c["status"] == "PENDING_REVIEW")
    c_id = pending_case["id"]
    pay_id = client.get(f"/api/payments/{c_id}/verify").json()["payment_id"]

    # Reject
    rej_resp = client.post(f"/api/investigations/{c_id}/reject", json={
        "action": "REJECT",
        "investigator_name": "Fraud Analyst",
        "reason": "False alarm"
    })
    assert rej_resp.status_code == 200

    # Attempt refund on rejected -> Blocked (403)
    blocked_resp = client.post(f"/api/payments/{pay_id}/refund", json={"amount": 500.0})
    assert blocked_resp.status_code == 403
    assert "rejected" in blocked_resp.json()["detail"].lower()

    # 2. Missing Capture ID / Invalid Payment ID -> 404
    missing_resp = client.post("/api/payments/NON_EXISTENT_PAYMENT/refund")
    assert missing_resp.status_code == 404

    # 3. Invalid Refund Amount (negative or exceeding total)
    # Approve another case
    other_case = None
    other_pay_id = None
    for candidate in cases:
        if candidate["id"] == c_id or candidate["status"] != "PENDING_REVIEW":
            continue
        verify_candidate = client.get(f"/api/payments/{candidate['id']}/verify")
        if verify_candidate.status_code == 200:
            other_case = candidate
            other_pay_id = verify_candidate.json()["payment_id"]
            break
    assert other_case is not None and other_pay_id is not None
    client.post(f"/api/investigations/{other_case['id']}/approve", json={
        "action": "APPROVE",
        "investigator_name": "Chief Risk Officer",
        "reason": "Confirmed fraud"
    })

    neg_resp = client.post(f"/api/payments/{other_pay_id}/refund", json={"amount": -50.0})
    assert neg_resp.status_code == 400
    assert "invalid refund amount" in neg_resp.json()["detail"].lower()

    excess_resp = client.post(f"/api/payments/{other_pay_id}/refund", json={"amount": 999999.0})
    assert excess_resp.status_code == 400
    assert "invalid refund amount" in excess_resp.json()["detail"].lower()

    # 4. Duplicate Refund Prevention (Idempotent response)
    # Valid refund
    first_refund = client.post(f"/api/payments/{other_pay_id}/refund", json={"amount": 100.0})
    assert first_refund.status_code == 200

    # Repeat same refund
    second_refund = client.post(f"/api/payments/{other_pay_id}/refund", json={"amount": 100.0})
    assert second_refund.status_code == 200
    assert second_refund.json()["status"] == "ALREADY_REFUNDED"
    assert second_refund.json()["refund_status"] == "COMPLETED"
