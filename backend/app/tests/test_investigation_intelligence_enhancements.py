import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/api/demo/seed")
        yield c

def test_paypal_sandbox_verification_endpoint_and_modes(client):
    """
    PRIORITY 1: Verify capture details, refundable balance, transaction linkage,
    and distinct labeling of simulated vs live Sandbox.
    """
    # 1. Fetch payments
    payments_resp = client.get("/api/payments")
    assert payments_resp.status_code == 200
    payments = payments_resp.json()
    assert len(payments) > 0
    target_payment = next(p for p in payments if p.get("capture_id"))
    payment_id = target_payment["id"]

    # 2. Call verification endpoint
    verify_resp = client.get(f"/api/payments/{payment_id}/verify")
    assert verify_resp.status_code == 200
    vdata = verify_resp.json()

    assert vdata["payment_id"] == payment_id
    assert "capture_id" in vdata and vdata["capture_id"] is not None
    assert vdata["captured_amount"] > 0
    assert vdata["currency"] == "USD"
    assert "refundable_balance" in vdata
    assert isinstance(vdata["is_simulated"], bool)
    assert vdata["integration_mode"] in ("LIVE_PAYPAL_SANDBOX", "SIMULATED_SANDBOX")
    assert "verification_source" in vdata
    assert "seller_protection" in vdata
    assert vdata["seller_protection"] == "ELIGIBLE"

def test_evidence_confidence_engine_fields(client):
    """
    PRIORITY 2: Every evidence record must provide confidence score, source reliability,
    corroboration count, observed vs baseline values, and alternative explanations.
    """
    cases_resp = client.get("/api/investigations")
    assert cases_resp.status_code == 200
    cases = cases_resp.json()
    assert len(cases) > 0
    case_id = cases[0]["id"]

    detail_resp = client.get(f"/api/investigations/{case_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    evidence_list = detail.get("evidence", [])
    assert len(evidence_list) > 0

    for ev in evidence_list:
        assert ev["evidence_type"] is not None
        assert ev["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert 0.0 <= ev["confidence_score"] <= 1.0
        assert ev["source_reliability"] is not None and len(ev["source_reliability"]) > 0
        assert ev["corroboration_count"] >= 1
        assert ev["observed_value"] is not None
        assert ev["baseline_value"] is not None
        assert ev["explanation"] is not None
        # Alternative hypothesis evaluation
        assert "alternative_explanation" in ev
        if ev["evidence_type"] in ("GEO_PROXY_IP", "DEVICE_SHARING"):
            # Ensure non-fraud legitimate explanations are present for nuanced signals
            assert ev["alternative_explanation"] is not None
            assert len(ev["alternative_explanation"]) > 10

def test_eight_stage_agent_reasoning_timeline(client):
    """
    PRIORITY 3: Visual timeline showing exactly 8 execution stages:
    1. Transaction anomaly detected
    2. Identity indicators examined
    3. Graph relationships discovered
    4. Evidence corroborated
    5. Risk score calculated
    6. Recommended action generated
    7. Human approval requested
    8. PayPal operation executed
    """
    cases_resp = client.get("/api/investigations")
    cases = cases_resp.json()
    case_id = cases[0]["id"]

    detail_resp = client.get(f"/api/investigations/{case_id}")
    detail = detail_resp.json()
    timeline = detail.get("reasoning_timeline", [])

    assert len(timeline) == 8, f"Expected 8 timeline stages, found {len(timeline)}"

    expected_stages = [
        "Transaction Anomaly Detected",
        "Identity Indicators Examined",
        "Graph Relationships Discovered",
        "Evidence Corroborated",
        "Risk Score Calculated",
        "Recommended Action Generated",
        "Human Approval Requested",
        "PayPal Operation Executed"
    ]

    for idx, expected_name in enumerate(expected_stages, start=1):
        stage = timeline[idx - 1]
        assert stage["stage_number"] == idx
        assert stage["stage_name"] == expected_name
        assert stage["status"] in ("COMPLETED", "IN_PROGRESS", "PENDING", "PENDING_APPROVAL", "PENDING_EXECUTION", "REJECTED", "FAILED")
        assert stage["actor"] is not None
        assert len(stage["summary"]) > 0

def test_deterministic_risk_score_exact_calculation(client):
    """
    PRIORITY 4: Exact mathematical breakdown when risk score is 100/100:
    Formula, contributing risk factors, raw sum, and clamping.
    """
    cases_resp = client.get("/api/investigations")
    cases = cases_resp.json()
    case_id = cases[0]["id"]

    detail_resp = client.get(f"/api/investigations/{case_id}")
    detail = detail_resp.json()
    scoring = detail.get("scoring_details", {})

    assert "deterministic_formula" in scoring
    assert "raw_sum_of_weights" in scoring
    assert "clamped_risk_score" in scoring
    assert scoring["clamped_risk_score"] == 100.0
    assert scoring["raw_sum_of_weights"] >= 100.0
    assert len(scoring.get("contributing_factors", [])) >= 5

    for factor in scoring["contributing_factors"]:
        assert "factor" in factor
        assert "weight" in factor
        assert factor["weight"] > 0
        assert "category" in factor
        assert "rationale" in factor

def test_financial_safety_approval_gates_and_reversal(client):
    """
    PRIORITY 5: Financial safety:
    - No automatic approval.
    - No duplicate refunds.
    - No refunds without valid captured payments.
    - Rejected cases cannot execute operations.
    """
    cases_resp = client.get("/api/investigations")
    cases = cases_resp.json()
    pending_case = next(c for c in cases if c["status"] == "PENDING_REVIEW")
    case_id = pending_case["id"]

    # 1. Attempt refund while PENDING_REVIEW -> Must fail with 403
    case_detail = client.get(f"/api/investigations/{case_id}").json()
    payment_op = case_detail["payment_operations"][0] if case_detail["payment_operations"] else None
    assert payment_op is not None
    payment_id = payment_op["id"]

    unauth_refund = client.post(f"/api/payments/{payment_id}/refund", json={"amount": 100.0})
    assert unauth_refund.status_code == 403
    assert "explicit human approval" in unauth_refund.json()["detail"].lower()

    # 2. Reject the case
    rej_resp = client.post(f"/api/investigations/{case_id}/reject", json={
        "action": "REJECT",
        "investigator_name": "Chief Security Officer",
        "reason": "False positive determined by manual phone verification"
    })
    assert rej_resp.status_code == 200

    # 3. Attempt refund on REJECTED case -> Must fail with 403
    rejected_refund = client.post(f"/api/payments/{payment_id}/refund", json={"amount": 100.0})
    assert rejected_refund.status_code == 403
    assert "rejected" in rejected_refund.json()["detail"].lower()
