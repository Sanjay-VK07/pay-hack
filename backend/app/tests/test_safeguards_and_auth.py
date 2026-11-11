"""
Tests for Priority 1 & 2 Safeguards:
- CASE_FRAUD_905 state mismatch detection and action blocking.
- Server rejects refund and capture on inconsistent or uncaptured records.
- Impossible and duplicate case transitions are rejected and audited.
- Mutation authentication guard blocks non-loopback and unauthenticated calls.
- Read-only demo access remains open.
"""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.config import settings
from app.database import SessionLocal
from app.models.models import InvestigationCase, PaymentOperation, AuditLog, Transaction
from app.services.approval_integrity import approval_integrity_state


def test_case_905_state_mismatch_flagged():
    """Verify CASE_FRAUD_905 is flagged as inconsistent and actions are blocked."""
    with SessionLocal() as db:
        case = db.query(InvestigationCase).filter(InvestigationCase.id == "CASE_FRAUD_905").first()
        assert case is not None
        valid, warning = approval_integrity_state(db, case)
        assert valid is False, "CASE_FRAUD_905 must be detected as having an integrity mismatch"
        assert warning is not None
        assert "blocked" in warning.lower()

    with TestClient(app) as client:
        resp = client.get("/api/investigations/CASE_FRAUD_905")
        assert resp.status_code == 200
        data = resp.json()
        assert data["approval_integrity_valid"] is False
        assert data["approval_integrity_warning"] is not None
        assert "blocked" in data["approval_integrity_warning"].lower()


def test_server_rejects_refund_on_uncaptured_pay_op_905():
    """Verify server rejects refund on PAY_OP_905 without calling PayPal."""
    with TestClient(app) as client:
        resp = client.post(
            "/api/payments/PAY_OP_905/refund",
            json={"reason": "Test refund", "investigator": "Test Auditor", "amount": 890.0, "currency": "USD"}
        )
        # Must be rejected (400, 403, or 409) because payment is UNCAPTURED with no capture ID
        assert resp.status_code in (400, 403, 409)
        detail = resp.json().get("detail", "")
        assert "uncaptured" in detail.lower() or "capture" in detail.lower() or "approval" in detail.lower()


def test_impossible_case_transition_rejected_and_audited():
    """Verify impossible transition from ACTION_COMPLETED to APPROVED or REJECTED is rejected and audited."""
    with SessionLocal() as db:
        case = db.query(InvestigationCase).filter(InvestigationCase.id == "CASE_FRAUD_904").first()
        assert case is not None
        assert case.status == "ACTION_COMPLETED"

    with TestClient(app) as client:
        # Attempt to approve an already completed case
        resp = client.post(
            "/api/investigations/CASE_FRAUD_904/approve",
            json={"action": "APPROVE", "investigator_name": "Test Investigator", "reason": "Illegal transition attempt"}
        )
        assert resp.status_code == 400
        assert "invalid state transition" in resp.json()["detail"].lower()

        # Attempt to reject an already completed case
        resp2 = client.post(
            "/api/investigations/CASE_FRAUD_904/reject",
            json={"action": "REJECT", "investigator_name": "Test Investigator", "reason": "Illegal rejection attempt"}
        )
        assert resp2.status_code == 400
        assert "invalid state transition" in resp2.json()["detail"].lower()

    # Check that TRANSITION_REJECTED was recorded in the audit trail
    with SessionLocal() as db:
        reject_audit = (
            db.query(AuditLog)
            .filter(AuditLog.case_id == "CASE_FRAUD_904", AuditLog.event_type == "TRANSITION_REJECTED")
            .order_by(AuditLog.created_at.desc())
            .first()
        )
        assert reject_audit is not None, "Rejected transition must be recorded in audit log"
        assert reject_audit.details.get("current_status") == "ACTION_COMPLETED"


def test_duplicate_case_transition_idempotent_and_audited():
    """Verify duplicate transition (rejecting an already rejected case) returns idempotent response and is audited."""
    with SessionLocal() as db:
        case = db.query(InvestigationCase).filter(InvestigationCase.id == "CASE_FRAUD_906").first()
        assert case is not None
        assert case.status == "REJECTED"

    with TestClient(app) as client:
        resp = client.post(
            "/api/investigations/CASE_FRAUD_906/reject",
            json={"action": "REJECT", "investigator_name": "Test Investigator", "reason": "Duplicate rejection"}
        )
        assert resp.status_code == 200
        assert resp.json()["approval_status"] == "REJECTED"
        assert "already rejected" in resp.json().get("message", "").lower()

    # Check that DUPLICATE_REJECTION_ATTEMPTED was recorded
    with SessionLocal() as db:
        dup_audit = (
            db.query(AuditLog)
            .filter(AuditLog.case_id == "CASE_FRAUD_906", AuditLog.event_type == "DUPLICATE_REJECTION_ATTEMPTED")
            .order_by(AuditLog.created_at.desc())
            .first()
        )
        assert dup_audit is not None


def test_non_loopback_unauthenticated_mutation_blocked():
    """Verify unauthenticated mutating request from non-loopback IP is rejected with 403 Forbidden."""
    # Temporarily ensure no key is configured
    orig_key = settings.AGENTSHIELD_API_KEY
    settings.AGENTSHIELD_API_KEY = ""
    try:
        with TestClient(app, client=("198.51.100.42", 54321)) as remote_client:
            resp = remote_client.post(
                "/api/demo/simulate-transaction",
                headers={"Host": "198.51.100.42:8000"}
            )
            assert resp.status_code == 403
            assert "non-loopback" in resp.json()["detail"].lower()
    finally:
        settings.AGENTSHIELD_API_KEY = orig_key


def test_authenticated_mutation_with_api_key():
    """Verify mutating routes enforce AGENTSHIELD_API_KEY when configured."""
    orig_key = settings.AGENTSHIELD_API_KEY
    settings.AGENTSHIELD_API_KEY = "test-secret-agentshield-key-xyz"
    try:
        with TestClient(app) as client:
            # 1. Unauthenticated -> 401
            resp_no_auth = client.post("/api/demo/simulate-transaction")
            assert resp_no_auth.status_code == 401
            assert "authentication required" in resp_no_auth.json()["detail"].lower()

            # 2. Wrong key -> 401
            resp_wrong_key = client.post(
                "/api/demo/simulate-transaction",
                headers={"X-AgentShield-Key": "wrong-key"}
            )
            assert resp_wrong_key.status_code == 401
            assert "invalid api key" in resp_wrong_key.json()["detail"].lower()

            # 3. Valid key -> allowed
            resp_valid = client.post(
                "/api/demo/simulate-transaction",
                headers={"X-AgentShield-Key": "test-secret-agentshield-key-xyz"}
            )
            assert resp_valid.status_code == 200
            assert resp_valid.json()["status"] == "SUCCESS"
    finally:
        settings.AGENTSHIELD_API_KEY = orig_key


def test_read_only_routes_remain_unauthenticated():
    """Verify all read-only endpoints remain accessible without credentials."""
    orig_key = settings.AGENTSHIELD_API_KEY
    settings.AGENTSHIELD_API_KEY = "enforced-key-for-test"
    try:
        with TestClient(app) as client:
            endpoints = [
                "/api/dashboard/summary",
                "/api/transactions?limit=5",
                "/api/fraud-networks",
                "/api/investigations?limit=5",
                "/api/payments?limit=5",
                "/api/audit?limit=5",
                "/api/demo/status",
            ]
            for ep in endpoints:
                resp = client.get(ep)
                assert resp.status_code == 200, f"Read-only endpoint {ep} failed with {resp.status_code}"
    finally:
        settings.AGENTSHIELD_API_KEY = orig_key


def test_database_isolation_prevents_writes_to_real_project_db():
    """Verify that tests execute against an isolated temporary database and cannot write to the real database."""
    import os
    import sqlite3

    real_db_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "agentshield.db")
    )
    assert os.path.exists(real_db_path), "Project database agentshield.db must exist"

    # Get initial count of audit logs in the real database
    with sqlite3.connect(real_db_path) as conn:
        initial_audit_count = conn.execute("SELECT count(*) FROM audit_logs").fetchone()[0]

    # Verify that SessionLocal is bound to a temporary database, not real_db_path
    with SessionLocal() as db:
        bind_url = str(db.get_bind().url)
        assert bind_url != f"sqlite:///{real_db_path}", "Test session must not be bound to real database"
        assert "test_agentshield_" in bind_url, "Test session must be bound to temporary test database"

    # Verify that the real database audit count was untouched
    with sqlite3.connect(real_db_path) as conn:
        final_audit_count = conn.execute("SELECT count(*) FROM audit_logs").fetchone()[0]
        assert final_audit_count == initial_audit_count, "Test writes must never mutate the real project database"

