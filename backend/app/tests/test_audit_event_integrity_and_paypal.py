import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, SessionLocal
from app.services.seed_service import SeedService

@pytest.fixture
def client():
    with TestClient(app) as c:
        db = SessionLocal()
        seed_svc = SeedService(db)
        seed_svc.clear_database()
        seed_svc.seed_demo_dataset()
        db.close()
        yield c

def test_audit_event_truthfulness_and_simulator_refund(client):
    """
    TASK 3 & 4: Verify that in simulator mode, SIMULATED_REFUND_EXECUTED is recorded
    with all 7 required fields, and never falsely records PAYPAL_REFUND_EXECUTED.
    """
    # 1. Get an existing pending review case
    cases_resp = client.get("/api/investigations")
    assert cases_resp.status_code == 200
    cases = cases_resp.json()
    case = next(c for c in cases if c["status"] == "PENDING_REVIEW")
    case_id = case["id"]

    # 2. Approve the case
    appr_resp = client.post(f"/api/investigations/{case_id}/approve", json={
        "action": "APPROVE",
        "investigator_name": "Chief Security Officer",
        "reason": "Deterministic fraud verification remediation"
    })
    assert appr_resp.status_code == 200

    # 3. Verify payment details
    verify_resp = client.get(f"/api/payments/{case_id}/verify")
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    payment_id = verify_data["payment_id"]
    capture_id = verify_data["capture_id"]

    # 4. Execute refund in simulator mode
    refund_resp = client.post(f"/api/payments/{payment_id}/refund", json={
        "amount": verify_data["captured_amount"],
        "reason": "Deterministic fraud verification remediation",
        "investigator": "Chief Security Officer"
    })
    assert refund_resp.status_code == 200
    refund_data = refund_resp.json()
    assert refund_data["status"] == "SUCCESS"
    assert refund_data["is_simulated"] is True

    # 5. Check Audit Log
    audit_resp = client.get(f"/api/audit?case_id={case_id}")
    assert audit_resp.status_code == 200
    audit_logs = audit_resp.json()
    
    sim_refund_events = [l for l in audit_logs if l["event_type"] == "SIMULATED_REFUND_EXECUTED"]
    assert len(sim_refund_events) >= 1
    
    event = sim_refund_events[0]
    # Check all required fields
    assert event["case_id"] == case_id
    assert event["transaction_id"] is not None
    details = event.get("details", {})
    assert details.get("capture_id") == capture_id
    assert details.get("refund_id") is not None
    assert details.get("api_response_status") == "SIMULATED_COMPLETED"
    assert details.get("timestamp") is not None
    assert details.get("actor") == "Chief Security Officer"
    assert details.get("is_simulated") is True

    # Verify no contradictory PAYPAL_REFUND_EXECUTED is recorded
    contradictory_events = [l for l in audit_logs if l["event_type"] == "PAYPAL_REFUND_EXECUTED"]
    assert len(contradictory_events) == 0

def test_paypal_live_refund_audit_workflow(client):
    """
    TASK 1, 2 & 3: Test that when live PayPal Sandbox credentials are active:
    - PAYPAL_REFUND_REQUESTED is recorded first
    - PayPal capture details are verified
    - Actual PayPal refund API is called
    - PAYPAL_REFUND_CONFIRMED is recorded on success with all required metadata
    """
    cases_resp = client.get("/api/investigations")
    cases = cases_resp.json()
    case = next(c for c in cases if c["status"] == "PENDING_REVIEW")
    case_id = case["id"]

    # Approve
    client.post(f"/api/investigations/{case_id}/approve", json={
        "action": "APPROVE",
        "investigator_name": "VP Financial Crime",
        "reason": "Confirmed unauthorized syndicate attack"
    })
    verify_data = client.get(f"/api/payments/{case_id}/verify").json()
    payment_id = verify_data["payment_id"]

    # Update payment capture_id to a live sandbox id format (not SIM-)
    db = SessionLocal()
    from app.models.models import PaymentOperation
    p_op = db.query(PaymentOperation).filter(PaymentOperation.id == payment_id).first()
    p_op.capture_id = "CAP_LIVE_SANDBOX_778899"
    p_op.is_simulated = False
    db.commit()
    db.close()

    # Mock PayPal Client and credentials to simulate live API flow
    with patch("app.api.payments.settings") as mock_settings, \
         patch("app.api.payments.PayPalClient") as mock_client_cls, \
         patch("app.api.payments.PayPalRefunds") as mock_refunds_cls:
        
        mock_settings.PAYPAL_CLIENT_ID = "mock_client_id_live"
        mock_settings.PAYPAL_CLIENT_SECRET = "mock_secret_live"
        mock_settings.PAYPAL_BASE_URL = "https://api-m.sandbox.paypal.com"

        mock_refunds = MagicMock()
        mock_refunds.get_capture_details.return_value = ({"status": "COMPLETED", "id": "CAP_LIVE_SANDBOX_778899"}, None)
        mock_refunds.refund_capture.return_value = ({"id": "REF_PAYPAL_SANDBOX_776655", "status": "COMPLETED"}, None)
        mock_refunds.get_refund_details.return_value = ({"id": "REF_PAYPAL_SANDBOX_776655", "status": "COMPLETED"}, None)
        mock_refunds_cls.return_value = mock_refunds

        captured_amt = verify_data["captured_amount"]
        refund_resp = client.post(f"/api/payments/{payment_id}/refund", json={
            "amount": captured_amt,
            "reason": "Real Sandbox Remediation",
            "investigator": "VP Financial Crime"
        })

        if refund_resp.status_code != 200:
            print("Refund error detail:", refund_resp.json())
        assert refund_resp.status_code == 200
        data = refund_resp.json()
        assert data["status"] == "SUCCESS"
        assert data["is_simulated"] is False
        assert data["paypal_reference"] == "REF_PAYPAL_SANDBOX_776655"

    # Verify Audit trail for live flow
    audit_resp = client.get(f"/api/audit?case_id={case_id}")
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    
    req_events = [l for l in logs if l["event_type"] == "PAYPAL_REFUND_REQUESTED"]
    conf_events = [l for l in logs if l["event_type"] == "PAYPAL_REFUND_CONFIRMED"]
    
    assert len(req_events) >= 1
    assert len(conf_events) >= 1
    
    conf_log = conf_events[0]
    assert conf_log["case_id"] == case_id
    assert conf_log["actor"] == "VP Financial Crime"
    assert conf_log["details"]["refund_id"] == "REF_PAYPAL_SANDBOX_776655"
    assert conf_log["details"]["api_response_status"] == "COMPLETED"
    assert conf_log["details"]["is_simulated"] is False
    assert conf_log["details"]["integration_mode"] == "LIVE_PAYPAL_SANDBOX"

def test_full_api_endpoints_suite(client):
    """
    TASK 5: Full API Testing across all specified endpoints:
    - GET /api/dashboard/summary
    - GET /api/transactions
    - POST /api/transactions/ingest
    - POST /api/transactions/{id}/analyze
    - GET /api/fraud-networks
    - GET /api/fraud-networks/{id}
    - GET /api/investigations
    - POST /api/investigations/{id}/run
    - POST /api/investigations/{id}/approve
    - POST /api/investigations/{id}/reject
    - POST /api/payments/orders/create
    - POST /api/payments/orders/{id}/capture
    - GET /api/payments/{id}/verify
    - POST /api/payments/{id}/refund
    """
    # 1. GET /api/dashboard/summary
    dash = client.get("/api/dashboard/summary")
    assert dash.status_code == 200
    assert "total_transactions_analyzed" in dash.json()

    # 2. GET /api/transactions
    txns = client.get("/api/transactions")
    assert txns.status_code == 200
    all_txns = txns.json()
    assert len(all_txns) > 0

    # 3. POST /api/transactions/ingest
    new_txn = {
        "customer_id": "ACC_001",
        "amount": 1499.99,
        "currency": "USD",
        "ip_address": "185.220.101.5",
        "device_fingerprint": "FP_TEST_TOR_88",
        "device_type": "EMULATOR",
        "merchant_name": "Test Ingestion Store"
    }
    ingest_resp = client.post("/api/transactions/ingest", json=new_txn)
    assert ingest_resp.status_code == 200
    ingest_data = ingest_resp.json()
    txn_id = ingest_data["id"]

    # 4. POST /api/transactions/{id}/analyze
    analyze_resp = client.post(f"/api/transactions/{txn_id}/analyze")
    assert analyze_resp.status_code == 200
    assert "risk_score" in analyze_resp.json()

    # 5. GET /api/fraud-networks
    fn_resp = client.get("/api/fraud-networks")
    assert fn_resp.status_code == 200
    fn_data = fn_resp.json()
    assert "nodes" in fn_data
    assert "edges" in fn_data
    assert len(fn_data["clusters"]) > 0

    # 6. GET /api/fraud-networks/{id}
    cluster_id = fn_data["clusters"][0]["id"]
    cluster_detail = client.get(f"/api/fraud-networks/{cluster_id}")
    assert cluster_detail.status_code == 200
    assert cluster_detail.json()["cluster"]["id"] == cluster_id

    # 7. GET /api/investigations
    inv_resp = client.get("/api/investigations")
    assert inv_resp.status_code == 200
    inv_list = inv_resp.json()
    assert len(inv_list) > 0
    test_case_id = inv_list[0]["id"]

    # 8. POST /api/investigations/{id}/run
    run_resp = client.post(f"/api/investigations/{test_case_id}/run")
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert "case_id" in run_data
    assert len(run_data["agent_executions"]) == 6

    # 9. POST /api/investigations/{id}/reject
    # Pick another case for rejection test
    case_to_reject = inv_list[1]["id"]
    rej_resp = client.post(f"/api/investigations/{case_to_reject}/reject", json={
        "action": "REJECT",
        "investigator_name": "Risk Officer Jane",
        "reason": "Legitimate high-value purchase confirmed with customer"
    })
    assert rej_resp.status_code == 200
    assert rej_resp.json()["approval_status"] == "REJECTED"

    # 10. POST /api/investigations/{id}/approve
    case_to_approve = inv_list[2]["id"]
    primary_txn_id = inv_list[2]["primary_transaction_id"]
    appr_resp = client.post(f"/api/investigations/{case_to_approve}/approve", json={
        "action": "APPROVE",
        "investigator_name": "Risk Officer Jane",
        "reason": "Confirmed syndicate fraud pattern"
    })
    assert appr_resp.status_code == 200
    assert appr_resp.json()["approval_status"] == "APPROVED"

    # 11. POST /api/payments/orders/create
    mismatch_order = client.post("/api/payments/orders/create", json={
        "case_id": case_to_approve,
        "transaction_ref": "TXN_UNRELATED_TEST",
        "amount": 350.0,
        "currency": "USD"
    })
    assert mismatch_order.status_code == 409

    order_resp = client.post("/api/payments/orders/create", json={
        "case_id": case_to_approve,
        "amount": 350.0,
        "currency": "USD"
    })
    assert order_resp.status_code == 200
    order_data = order_resp.json()
    assert order_data["transaction_ref"] == primary_txn_id
    order_id = order_data["paypal_order_id"]

    # 12. POST /api/payments/orders/{id}/capture
    capture_resp = client.post(f"/api/payments/orders/{order_id}/capture")
    assert capture_resp.status_code == 200
    cap_data = capture_resp.json()
    assert cap_data["payment_status"] == "CAPTURED"
    capture_id = cap_data["capture_id"]

    # Repeating capture must reuse the recorded capture instead of making another.
    capture_replay = client.post(f"/api/payments/orders/{order_id}/capture")
    assert capture_replay.status_code == 200
    assert capture_replay.json()["capture_id"] == capture_id
    assert capture_replay.json()["idempotent_replay"] is True
    assert client.post("/api/payments/orders/UNKNOWN_ORDER/capture").status_code == 404

    # 13. GET /api/payments/{id}/verify
    verify_resp = client.get(f"/api/payments/{order_data['payment_id']}/verify")
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert verify_data["payment_status"] == "CAPTURED"
    assert verify_data["refundable_balance"] == 350.0

    # 14. POST /api/payments/{id}/refund
    refund_resp = client.post(f"/api/payments/{order_data['payment_id']}/refund", json={
        "amount": 350.0,
        "investigator": "Risk Officer Jane",
        "reason": "Syndicate mitigation"
    })
    assert refund_resp.status_code == 200
    ref_data = refund_resp.json()
    assert ref_data["status"] == "SUCCESS"
    assert ref_data["refund_status"] == "COMPLETED"

def test_dynamic_settings_status_probe(client):
    """
    TASK 4: Verify Settings returns actual dynamic verification state:
    - credentials status
    - oauth status
    - connectivity
    - integration mode
    - last verification
    """
    status_resp = client.get("/api/demo/status")
    assert status_resp.status_code == 200
    status = status_resp.json()
    
    assert "paypal_credentials_status" in status
    assert "paypal_oauth_status" in status
    assert "paypal_connectivity" in status
    assert "integration_mode" in status
    assert "last_api_verification" in status
    assert "deterministic_engine_active" in status
    assert status["deterministic_engine_active"] is True

def test_case_fraud_905_uncaptured_truthfulness_and_reversal_safety(client):
    """
    Verify that CASE_FRAUD_905 accurately reflects that no settled PayPal capture
    exists in Payment Operations without fabricating mock payment records.
    """
    client.post("/api/demo/seed")
    resp = client.get("/api/investigations/CASE_FRAUD_905")
    assert resp.status_code == 200
    data = resp.json()
    
    # Assert truthful uncaptured fields
    assert data["paypal_eligible"] is False
    assert data["capture_id"] is None
    assert data["status"] == "PENDING_REVIEW"
    assert data["approval_status"] == "PENDING"
    assert data["approval_requests"][-1]["status"] == "PENDING"
    
    # Assert paypal_verification raw details
    pv = data["paypal_verification"]
    assert pv["eligible_for_refund"] is False
    assert pv["captured_amount"] == 0.0
    assert pv["refundable_balance"] == 0.0
    verify_resp = client.get("/api/payments/CASE_FRAUD_905/verify")
    assert verify_resp.status_code == 409
    assert "no valid completed capture" in verify_resp.json()["detail"].lower()
    assert pv["status"] == "UNCAPTURED"
    assert pv["seller_protection"] == "INELIGIBLE_NO_CAPTURE"

    # Assert TXN_FRAUD_905 is present in Payment Operations as an uncaptured, ineligible operation
    payments_resp = client.get("/api/payments")
    assert payments_resp.status_code == 200
    all_payments = payments_resp.json()
    p_905 = next(p for p in all_payments if p["transaction_ref"] == "TXN_FRAUD_905")
    assert p_905["id"] == "PAY_OP_905"
    assert p_905["capture_id"] is None
    assert p_905["payment_status"] == "UNCAPTURED"
    assert p_905["refund_status"] == "INELIGIBLE"

    # Assert refund execution is blocked by the gateway with 400 Bad Request
    refund_attempt = client.post(f"/api/payments/{p_905['id']}/refund", json={
        "amount": 890.0,
        "investigator": "Test Officer",
        "reason": "Unauthorized refund attempt on uncaptured txn"
    })
    assert refund_attempt.status_code == 400
    assert "Only COMPLETED or CAPTURED payments are eligible" in refund_attempt.json()["detail"]

    # Assert stage 8 reasoning timeline shows accurate uncaptured status
    stage_8 = next(s for s in data["reasoning_timeline"] if s["stage_number"] == 8)
    assert stage_8["status"] == "NOT_ELIGIBLE_NO_CAPTURE"
    assert "No settled PayPal capture record exists" in stage_8["summary"]


def test_identity_timeline_uses_transaction_device_source_of_truth(client):
    from app.models.models import Transaction

    case_id = "CASE_FRAUD_906"
    detail = client.get(f"/api/investigations/{case_id}").json()
    with SessionLocal() as db:
        txn = db.query(Transaction).filter(Transaction.id == detail["primary_transaction_id"]).first()
        expected_fingerprint = txn.device.device_fingerprint

    identity_stage = next(stage for stage in detail["reasoning_timeline"] if stage["stage_number"] == 2)
    assert identity_stage["raw_data"]["findings"]["device_fingerprint"] == expected_fingerprint
    assert expected_fingerprint in identity_stage["summary"]
    assert "EMUL-BLU-42" not in identity_stage["summary"]


def test_refund_rejects_processing_payment_without_second_gateway_call(client):
    from app.models.models import PaymentOperation

    db = SessionLocal()
    payment = db.query(PaymentOperation).filter(PaymentOperation.id == "PAY_OP_906").first()
    payment.refund_status = "PROCESSING"
    db.commit()
    db.close()

    response = client.post("/api/payments/PAY_OP_906/refund")
    assert response.status_code == 409
    assert "in progress" in response.json()["detail"].lower()


def test_missing_live_credentials_never_falls_back_or_claims_refund(client):
    from app.models.models import InvestigationCase, PaymentOperation

    client.post("/api/investigations/CASE_FRAUD_906/approve", json={
        "action": "APPROVE",
        "investigator_name": "Test Reviewer",
        "reason": "Sandbox verification only",
    })
    db = SessionLocal()
    payment = db.query(PaymentOperation).filter(PaymentOperation.id == "PAY_OP_906").first()
    payment.is_simulated = False
    db.commit()
    db.close()

    response = client.post("/api/payments/PAY_OP_906/refund")
    assert response.status_code == 503
    assert "no simulator fallback" in response.json()["detail"].lower()

    db = SessionLocal()
    payment = db.query(PaymentOperation).filter(PaymentOperation.id == "PAY_OP_906").first()
    case = db.query(InvestigationCase).filter(InvestigationCase.id == "CASE_FRAUD_906").first()
    assert payment.refund_status == "NONE"
    assert case.status == "APPROVED"
    db.close()


def test_live_refund_pending_response_is_not_reported_as_completed(client):
    from app.models.models import AuditLog, InvestigationCase, PaymentOperation, Transaction

    client.post("/api/investigations/CASE_FRAUD_906/approve", json={
        "action": "APPROVE",
        "investigator_name": "Test Reviewer",
        "reason": "Sandbox verification only",
    })
    db = SessionLocal()
    payment = db.query(PaymentOperation).filter(PaymentOperation.id == "PAY_OP_906").first()
    payment.is_simulated = False
    payment.capture_id = "CAP_LIVE_PENDING_906"
    db.commit()
    db.close()

    with patch("app.api.payments.settings") as mock_settings, \
         patch("app.api.payments.PayPalClient"), \
         patch("app.api.payments.PayPalRefunds") as mock_refunds_cls:
        mock_settings.PAYPAL_CLIENT_ID = "mock_client_id_live"
        mock_settings.PAYPAL_CLIENT_SECRET = "mock_secret_live"
        mock_refunds = MagicMock()
        mock_refunds.get_capture_details.return_value = ({
            "status": "COMPLETED",
            "id": "CAP_LIVE_PENDING_906",
            "amount": {"value": "2150.00", "currency_code": "USD"},
        }, None)
        mock_refunds.refund_capture.return_value = ({"id": "REF_PENDING_906", "status": "PENDING"}, None)
        mock_refunds.get_refund_details.return_value = ({"id": "REF_PENDING_906", "status": "PENDING"}, None)
        mock_refunds_cls.return_value = mock_refunds

        response = client.post("/api/payments/PAY_OP_906/refund")
        mock_refunds.get_refund_details.return_value = ({"id": "REF_PENDING_906", "status": "COMPLETED"}, None)
        verified = client.post("/api/payments/PAY_OP_906/refund/verify")

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING_CONFIRMATION"
    assert response.json()["refund_status"] == "PROCESSING"
    assert verified.status_code == 200
    assert verified.json()["refund_status"] == "COMPLETED"
    db = SessionLocal()
    payment = db.query(PaymentOperation).filter(PaymentOperation.id == "PAY_OP_906").first()
    txn = db.query(Transaction).filter(Transaction.id == "TXN_FRAUD_906").first()
    case = db.query(InvestigationCase).filter(InvestigationCase.id == "CASE_FRAUD_906").first()
    assert payment.refund_status == "COMPLETED"
    assert payment.payment_status == "REFUNDED"
    assert txn.payment_status == "REFUNDED"
    assert txn.investigation_status == "RESOLVED"
    assert case.status == "ACTION_COMPLETED"
    assert db.query(AuditLog).filter(AuditLog.case_id == case.id, AuditLog.event_type == "PAYPAL_REFUND_PENDING").count() == 1
    assert db.query(AuditLog).filter(AuditLog.case_id == case.id, AuditLog.event_type == "PAYPAL_REFUND_CONFIRMED").count() == 1
    db.close()

def test_transactions_extended_search_criteria(client):
    """
    Verify transaction search works across transaction ID, customer name, email, account number, and IP.
    """
    client.post("/api/demo/seed")
    
    # Search by transaction ID
    r1 = client.get("/api/transactions?search=TXN_FRAUD_901")
    assert r1.status_code == 200
    txns1 = r1.json()
    assert len(txns1) >= 1
    assert any(t["id"] == "TXN_FRAUD_901" for t in txns1)
    
    # Search by IP address
    r2 = client.get("/api/transactions?search=185.220.101.5")
    assert r2.status_code == 200
    txns2 = r2.json()
    assert len(txns2) >= 1
    assert any(t["ip_address"] == "185.220.101.5" for t in txns2)
    
    # Search by customer name
    r3 = client.get("/api/transactions?search=David")
    assert r3.status_code == 200
    txns3 = r3.json()
    assert len(txns3) >= 1
    assert any("David" in (t.get("customer_name") or "") for t in txns3)

def test_dashboard_dynamic_metrics_and_trend(client):
    """
    Verify dashboard metrics are derived dynamically from backend data.
    """
    client.post("/api/demo/seed")
    resp = client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    
    assert "legitimate_transactions" in data
    assert "total_cases_count" in data
    assert "total_agent_executions_count" in data
    assert "daily_trend" in data
    
    assert data["legitimate_transactions"] + data["suspicious_transactions"] == data["total_transactions_analyzed"]
    assert data["total_cases_count"] >= 1
    assert data["total_agent_executions_count"] >= 1
    assert len(data["daily_trend"]) == 7
