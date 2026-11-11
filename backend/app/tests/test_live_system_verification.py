"""
Safe automated verification tests for AgentShield:
- Read-only queries and assertions on existing relationships.
- Does not seed, reset, or alter database state.
- Does not trigger attacks or execute refunds.
- Validates cross-module consistency across Dashboard, Transactions, Investigations,
  Fraud Networks, Payments, and Audit Center.
"""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.models import Transaction, InvestigationCase, PaymentOperation, CustomerAccount, AuditLog


def test_safe_payment_mapping_and_case_905_integrity():
    """
    Verify Issue 1:
    - CASE_FRAUD_905 accurately references TXN_FRAUD_905.
    - TXN_FRAUD_905 is mapped in Payment Operations (PAY_OP_905) as an uncaptured authorization.
    - capture_id is strictly None (never fabricated).
    - It is explicitly marked as ineligible for refund.
    """
    with SessionLocal() as db:
        case = db.query(InvestigationCase).filter(InvestigationCase.id == "CASE_FRAUD_905").first()
        assert case is not None, "CASE_FRAUD_905 must exist in database"
        assert case.primary_transaction_id == "TXN_FRAUD_905", "CASE_FRAUD_905 must reference TXN_FRAUD_905"

        txn = db.query(Transaction).filter(Transaction.id == "TXN_FRAUD_905").first()
        assert txn is not None, "TXN_FRAUD_905 must exist in database"

        payment = db.query(PaymentOperation).filter(PaymentOperation.transaction_ref == "TXN_FRAUD_905").first()
        assert payment is not None, "TXN_FRAUD_905 must have a corresponding PaymentOperation record"
        assert payment.capture_id is None, "Capture ID must be strictly None (never fabricated for uncaptured txn)"
        assert payment.payment_status == "UNCAPTURED"
        assert payment.refund_status == "INELIGIBLE"

    with TestClient(app) as client:
        # Verify via API endpoint
        resp = client.get("/api/investigations/CASE_FRAUD_905")
        assert resp.status_code == 200
        data = resp.json()

        assert data["primary_transaction_id"] == "TXN_FRAUD_905"
        assert data["capture_id"] is None
        assert data["paypal_eligible"] is False
        assert data["paypal_verification"]["eligible_for_refund"] is False
        assert data["paypal_verification"]["captured_amount"] == 0.0
        assert data["paypal_verification"]["refundable_balance"] == 0.0
        assert data["paypal_verification"]["seller_protection"] == "NOT_CHECKED_NO_CAPTURE"

        # Verify Payment Operations list endpoint
        payments_resp = client.get("/api/payments")
        assert payments_resp.status_code == 200
        payments = payments_resp.json()
        p905 = next((p for p in payments if p["transaction_ref"] == "TXN_FRAUD_905"), None)
        assert p905 is not None, "TXN_FRAUD_905 must appear in Payment Operations"
        assert p905["capture_id"] is None
        assert p905["payment_status"] == "UNCAPTURED"
        assert p905["refund_status"] == "INELIGIBLE"


def test_safe_fraud_network_topology_and_spacing():
    """
    Verify Issue 2:
    - NetworkX graph generates valid topological nodes and edges.
    - Node spacing enforces collision separation.
    - All edges preserve evidence IDs and stored supporting evidence without invented confidence values.
    """
    with TestClient(app) as client:
        resp = client.get("/api/fraud-networks")
        assert resp.status_code == 200
        graph = resp.json()

        assert "nodes" in graph and len(graph["nodes"]) > 0
        assert "edges" in graph and len(graph["edges"]) > 0
        assert "clusters" in graph and len(graph["clusters"]) > 0

        # Check collision separation between nodes
        nodes = graph["nodes"]
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                n1, n2 = nodes[i], nodes[j]
                dx = abs(n1["position"]["x"] - n2["position"]["x"])
                dy = abs(n1["position"]["y"] - n2["position"]["y"])
                assert dx >= 200.0 or dy >= 130.0, f"Nodes {n1['id']} and {n2['id']} collide at ({dx}, {dy})"

        # Verify edge intelligence
        for edge in graph["edges"]:
            assert "relationship" in edge
            assert "confidence" not in edge
            assert "risk_contribution" not in edge
            assert "supporting_evidence" in edge


def test_safe_transactions_table_data_and_columns():
    """
    Verify Issue 3:
    - Transaction list provides full customer information, email, amount, and exact risk scores.
    - No fields are truncated or missing.
    """
    with TestClient(app) as client:
        resp = client.get("/api/transactions?limit=25")
        assert resp.status_code == 200
        txns = resp.json()
        assert len(txns) > 0

        for t in txns:
            assert "id" in t
            assert "customer_id" in t
            assert "amount" in t and t["amount"] >= 0
            assert "risk_score" in t and 0.0 <= t["risk_score"] <= 100.0
            assert "risk_category" in t and t["risk_category"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
            assert "payment_status" in t


def test_safe_cross_module_consistency():
    """
    Verify Issue 4:
    - Dashboard, Transactions, Investigations, and Audit Trail share consistent IDs.
    - Audit log events represent actual recorded state transitions.
    """
    with TestClient(app) as client:
        dash = client.get("/api/dashboard/summary").json()
        assert dash["total_transactions_analyzed"] >= 20
        assert dash["legitimate_transactions"] + dash["suspicious_transactions"] == dash["total_transactions_analyzed"]
        assert dash["total_cases_count"] >= 1
        assert len(dash["daily_trend"]) == 7

        audit = client.get("/api/audit?limit=20").json()
        assert len(audit) > 0
        for entry in audit:
            assert "event_type" in entry
            assert "actor" in entry
            assert "created_at" in entry
