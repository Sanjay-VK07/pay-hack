import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.models import InvestigationCase, PaymentOperation, Transaction, CustomerAccount

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/api/demo/seed")
        yield c

def test_evidence_records_fidelity_and_count_matching(client):
    """
    PRIORITY 2: Verify that displayed evidence count equals actual associated evidence records,
    and every record contains observed value, baseline value, and relevance explanation.
    """
    cases_resp = client.get("/api/investigations")
    assert cases_resp.status_code == 200
    cases = cases_resp.json()
    assert len(cases) > 0

    for c in cases:
        case_id = c["id"]
        detail_resp = client.get(f"/api/investigations/{case_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()

        # Displayed evidence count MUST strictly equal actual evidence records count
        assert detail["evidence_count"] == len(detail["evidence"])
        assert c["evidence_count"] == len(detail["evidence"])

        # Check evidence structure integrity
        for ev in detail["evidence"]:
            assert ev["id"] is not None
            assert ev["evidence_type"] is not None
            assert ev["observed_value"] is not None
            assert ev["baseline_value"] is not None
            assert ev["explanation"] is not None
            assert ev["severity"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
            assert ev["verification_status"] in ("VERIFIED", "CORROBORATED")

def test_case_data_integrity_no_silent_unknowns(client):
    """
    PRIORITY 1: Ensure cases reference valid transactions with real customers and non-zero amounts.
    Never use 'Unknown' or '$0.00' as a silent fallback when actual data exists.
    """
    cases_resp = client.get("/api/investigations")
    cases = cases_resp.json()

    for c in cases:
        assert c["customer_name"] != "Unknown"
        assert c["customer_name"] is not None
        assert c["primary_transaction_id"] is not None
        if c["transaction_amount"] is not None:
            assert c["transaction_amount"] > 0.0
            assert c["currency"] == "USD"

def test_investigation_status_lifecycle_and_transitions(client):
    """
    PRIORITY 3: Case starts in PENDING_REVIEW (never auto-approved).
    Approving transitions to APPROVED. Rejection prevents actions.
    """
    case_id = "CASE_FRAUD_902"
    detail_before = client.get(f"/api/investigations/{case_id}").json()
    assert detail_before["status"] == "PENDING_REVIEW"
    assert detail_before["approval_status"] == "PENDING"

    # Approve
    app_resp = client.post(f"/api/investigations/{case_id}/approve", json={
        "action": "APPROVE",
        "investigator_name": "Chief Fraud Officer",
        "reason": "Corroborated emulator and card cloning network"
    })
    assert app_resp.status_code == 200
    app_data = app_resp.json()
    assert app_data["approval_status"] == "APPROVED"
    assert "operation_reference" in app_data

    # Verify case status is now APPROVED
    detail_after = client.get(f"/api/investigations/{case_id}").json()
    assert detail_after["status"] == "APPROVED"
    assert detail_after["approval_status"] == "APPROVED"
    assert detail_after["approving_user"] == "Chief Fraud Officer"

def test_human_approval_gate_and_rejection_blocking(client):
    """
    PRIORITY 4: Human approval gate enforcement.
    Rejecting a case blocks refunds completely.
    """
    case_id = "CASE_FRAUD_904"
    rej_resp = client.post(f"/api/investigations/{case_id}/reject", json={
        "action": "REJECT",
        "investigator_name": "Senior Investigator",
        "reason": "User confirmed transaction was authorized out-of-band"
    })
    assert rej_resp.status_code == 200

    detail = client.get(f"/api/investigations/{case_id}").json()
    assert detail["status"] == "REJECTED"
    assert detail["approval_status"] == "REJECTED"

    # Attempting to refund rejected operation must fail with 403 Forbidden
    refund_resp = client.post("/api/payments/PAY_OP_904/refund", json={
        "payment_id": "PAY_OP_904",
        "reason": "Unauthorized charge reversal"
    })
    assert refund_resp.status_code == 403
    assert "rejected" in refund_resp.json()["detail"].lower()

def test_paypal_financial_validation_ten_steps(client):
    """
    PRIORITY 5: Financial validation before refunds.
    1. Verify PayPal payment exists
    2. Verify captured status
    3. Retrieve capture ID
    4. Verify refundable amount
    5. Check already refunded
    6. Verify human approval
    7-9. Execute refund & verify response
    10. Record reference in audit log
    """
    # 1. Nonexistent payment -> 404
    nonexist_resp = client.post("/api/payments/PAY_NONEXISTENT/refund")
    assert nonexist_resp.status_code == 404

    # 2. Unapproved payment -> 403 Forbidden
    unapproved_resp = client.post("/api/payments/PAY_OP_906/refund")
    assert unapproved_resp.status_code == 403
    assert "human approval" in unapproved_resp.json()["detail"].lower()

    # Approve CASE_FRAUD_906 first
    client.post("/api/investigations/CASE_FRAUD_906/approve", json={
        "action": "APPROVE",
        "investigator_name": "Risk Director",
        "reason": "Confirmed unauthorized bot transactions"
    })

    # 3. Invalid refund amount (> captured total) -> 400
    invalid_amt_resp = client.post("/api/payments/PAY_OP_906/refund", json={
        "payment_id": "PAY_OP_906",
        "amount": 999999.00
    })
    assert invalid_amt_resp.status_code == 400
    assert "invalid refund amount" in invalid_amt_resp.json()["detail"].lower()

    # 4. Valid refund on approved payment -> 200 with verified response
    valid_refund_resp = client.post("/api/payments/PAY_OP_906/refund", json={
        "payment_id": "PAY_OP_906",
        "amount": 2150.00,
        "reason": "AgentShield automated remediation",
        "investigator": "Risk Director"
    })
    assert valid_refund_resp.status_code == 200
    refund_data = valid_refund_resp.json()
    assert refund_data["refund_status"] == "COMPLETED"
    assert refund_data["case_status"] == "ACTION_COMPLETED"
    assert "paypal_reference" in refund_data

    # 5. Duplicate refund attempt -> ALREADY_REFUNDED idempotent response
    dup_refund_resp = client.post("/api/payments/PAY_OP_906/refund")
    assert dup_refund_resp.status_code == 200
    assert dup_refund_resp.json()["status"] == "ALREADY_REFUNDED"

def test_duplicate_case_and_attack_prevention(client):
    """
    PRIORITY 6: Idempotency and deduplication. Repeated trigger attack
    or run investigation should NOT generate unlimited duplicate cases.
    """
    cases_before = len(client.get("/api/investigations").json())

    # Trigger attack 3 times in a row
    r1 = client.post("/api/demo/trigger-suspicious")
    assert r1.status_code == 200
    r2 = client.post("/api/demo/trigger-suspicious")
    assert r2.status_code == 200
    r3 = client.post("/api/demo/trigger-suspicious")
    assert r3.status_code == 200

    cases_after = len(client.get("/api/investigations").json())
    # Should only add AT MOST 1 case (stable ID CASE_ATTACK_999), not 3!
    assert cases_after <= cases_before + 1

    # Run full investigation on TXN_FRAUD_901 twice
    run1 = client.post("/api/demo/run-investigation")
    assert run1.status_code == 200
    run2 = client.post("/api/demo/run-investigation")
    assert run2.status_code == 200

    cases_final = len(client.get("/api/investigations").json())
    assert cases_final == cases_after
