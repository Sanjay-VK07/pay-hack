import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HEALTHY"

def test_dashboard_summary_endpoint(client):
    resp = client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_transactions_analyzed" in data
    assert "suspicious_transactions" in data
    assert "fraud_networks_discovered" in data
    assert data["total_transactions_analyzed"] >= 25

def test_transactions_endpoints(client):
    # List
    resp = client.get("/api/transactions")
    assert resp.status_code == 200
    txns = resp.json()
    assert len(txns) > 0
    
    # Detail
    first_id = txns[0]["id"]
    detail_resp = client.get(f"/api/transactions/{first_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == first_id

def test_fraud_networks_endpoint(client):
    resp = client.get("/api/fraud-networks")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert "clusters" in data
    assert data["total_nodes"] > 10

def test_investigations_and_approval_flow(client):
    # Run multi-agent investigation on TXN_FRAUD_901
    analyze_resp = client.post("/api/transactions/TXN_FRAUD_901/analyze")
    assert analyze_resp.status_code == 200
    data = analyze_resp.json()
    assert data["risk_level"] == "CRITICAL"
    case_id = data["case_id"]
    
    # Approve case
    appr_resp = client.post(f"/api/investigations/{case_id}/approve", json={
        "action": "APPROVE",
        "investigator_name": "Chief Risk Officer",
        "reason": "Confirmed multi-account coordinated syndicate link"
    })
    assert appr_resp.status_code == 200
    assert appr_resp.json()["approval_status"] == "APPROVED"

def test_payments_and_refund_endpoint(client):
    resp = client.get("/api/payments")
    assert resp.status_code == 200
    payments = resp.json()
    assert len(payments) > 0

    # Ensure payment PAY_OP_901 can be refunded after approval
    ref_resp = client.post("/api/payments/PAY_OP_901/refund", json={
        "payment_id": "PAY_OP_901",
        "reason": "AgentShield automated remediation"
    })
    assert ref_resp.status_code == 200
    ref_data = ref_resp.json()
    assert ref_data["refund_status"] == "COMPLETED"

def test_audit_log_endpoint(client):
    resp = client.get("/api/audit")
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) > 0
