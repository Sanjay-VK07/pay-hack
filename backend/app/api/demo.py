import uuid
from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.services.seed_service import SeedService
from app.models.models import Transaction, AuditLog, PaymentOperation
from app.fraud.risk_engine import DeterministicRiskEngine
from app.agents.orchestrator import MultiAgentOrchestrator

def utcnow():
    return datetime.now(timezone.utc)

from app.agents.llm_service import llm_service
from app.paypal.auth import PayPalAuth

router = APIRouter(prefix="/demo", tags=["Demo Mode"])

@router.get("/status")
def get_demo_status():
    status = llm_service.get_provider_status()
    paypal_auth = PayPalAuth()
    paypal_status = paypal_auth.test_connectivity()

    return {
        "demo_mode": settings.DEMO_MODE,
        "ai_provider": settings.AI_PROVIDER,
        "active_provider": status["active_provider"],
        "providers": status["providers"],
        "has_gemini": bool(settings.GEMINI_API_KEY),
        "has_openai": bool(settings.OPENAI_API_KEY),
        "has_paypal_sandbox": paypal_status["credentials_status"] == "CONFIGURED",
        "paypal_credentials_status": paypal_status["credentials_status"],
        "paypal_oauth_status": paypal_status["oauth_status"],
        "paypal_connectivity": paypal_status["connectivity"],
        "integration_mode": paypal_status["mode"],
        "last_api_verification": paypal_status["last_api_verification"],
        "paypal_error_detail": paypal_status.get("error_detail"),
        "paypal_base_url": settings.PAYPAL_BASE_URL,
        "deterministic_engine_active": True
    }

@router.post("/seed")
def seed_demo(db: Session = Depends(get_db)):
    svc = SeedService(db)
    svc.clear_database()
    count = svc.seed_demo_dataset()

    audit = AuditLog(
        id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_SEED",
        event_type="DEMO_DATASET_LOADED",
        actor="DEMO_ORCHESTRATOR",
        previous_state=None,
        new_state="SEEDED",
        api_ref="/api/demo/seed",
        details={"accounts_seeded": 12, "transactions_seeded": count}
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "message": f"Seeded {count} marketplace transactions and 12 customer accounts.",
        "transactions_count": count
    }

@router.post("/reset")
def reset_demo(db: Session = Depends(get_db)):
    svc = SeedService(db)
    svc.clear_database()

    audit = AuditLog(
        id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_RESET",
        event_type="DEMO_DATASET_RESET",
        actor="DEMO_ORCHESTRATOR",
        previous_state="ACTIVE",
        new_state="RESET",
        api_ref="/api/demo/reset",
        details={}
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "message": "Demo database successfully cleared to clean state."
    }

@router.post("/simulate-transaction")
def simulate_legitimate_transaction(db: Session = Depends(get_db)):
    tx_id = f"TXN_SIM_{uuid.uuid4().hex[:6].upper()}"
    new_txn = Transaction(
        id=tx_id,
        customer_id="ACC_001",
        amount=65.50,
        currency="USD",
        timestamp=utcnow(),
        payment_status="COMPLETED",
        risk_score=12.0,
        risk_category="LOW",
        device_id="DEV_001",
        ip_address="73.189.44.12",
        payment_identity_id="PID_001",
        investigation_status="NONE",
        merchant_name="Apex Global Electronics"
    )
    db.add(new_txn)
    
    audit = AuditLog(
        id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{tx_id}",
        transaction_id=tx_id,
        event_type="SIMULATED_TRANSACTION_EMITTED",
        actor="DEMO_SIMULATOR",
        previous_state=None,
        new_state="LOW",
        api_ref="/api/demo/simulate-transaction",
        details={"amount": 65.50, "type": "LEGITIMATE"}
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "transaction_id": tx_id,
        "amount": 65.50,
        "risk_level": "LOW",
        "message": "Simulated legitimate checkout event."
    }

@router.post("/trigger-suspicious")
def trigger_suspicious_activity(db: Session = Depends(get_db)):
    """
    Triggers a rapid velocity and credential-sharing attack vector on Marcus Sterling (ACC_009).
    Uses stable identifiers and idempotency to prevent duplicate cases and transactions.
    """
    stable_tx_id = "TXN_ATTACK_999"
    stable_case_id = "CASE_ATTACK_999"
    stable_pay_id = "PAY_OP_ATTACK_999"

    attack_txn = db.query(Transaction).filter(Transaction.id == stable_tx_id).first()
    if attack_txn:
        # Idempotently refresh existing attack transaction
        attack_txn.amount = 2890.00
        attack_txn.timestamp = utcnow()
        attack_txn.payment_status = "COMPLETED"
        attack_txn.risk_score = 98.0
        attack_txn.risk_category = "CRITICAL"
        attack_txn.investigation_status = "PENDING"
    else:
        attack_txn = Transaction(
            id=stable_tx_id,
            customer_id="ACC_009",
            amount=2890.00,
            currency="USD",
            timestamp=utcnow(),
            payment_status="COMPLETED",
            risk_score=98.0,
            risk_category="CRITICAL",
            device_id="DEV_007",  # Emulator
            ip_address="185.220.101.5",  # Tor exit proxy
            payment_identity_id="PID_006",  # Stolen Card
            investigation_status="PENDING",
            merchant_name="Apex Luxury Watch Co."
        )
        db.add(attack_txn)

    db.flush()

    # Instant multi-agent investigation dispatch (idempotent run creates the case first)
    orchestrator = MultiAgentOrchestrator(db)
    result = orchestrator.run_investigation(transaction_id=stable_tx_id, force_new_case=False)
    created_case_id = result.get("case_id", stable_case_id)

    # Ensure captured payment record exists for PayPal financial validation flow (now referencing verified case)
    pay_op = db.query(PaymentOperation).filter(PaymentOperation.id == stable_pay_id).first()
    if pay_op:
        pay_op.amount = 2890.00
        pay_op.case_id = created_case_id
        pay_op.payment_status = "COMPLETED"
        pay_op.refund_status = "NONE"
        pay_op.approval_status = "PENDING"
    else:
        pay_op = PaymentOperation(
            id=stable_pay_id,
            case_id=created_case_id,
            paypal_order_id="SANDBOX-ORD-ATTACK-999",
            capture_id="CAP-SANDBOX-ATTACK-999",
            transaction_ref=stable_tx_id,
            amount=2890.00,
            currency="USD",
            payment_status="COMPLETED",
            refund_status="NONE",
            approval_status="PENDING",
            operation_type="REFUND",
            idempotency_key=f"IDEM_REFUND_{stable_tx_id}",
            is_simulated=True,
            raw_response={
                "status": "COMPLETED",
                "capture_id": "CAP-SANDBOX-ATTACK-999",
                "seller_protection": {"status": "ELIGIBLE"},
                "amount": {"value": "2890.00", "currency_code": "USD"}
            }
        )
        db.add(pay_op)

    db.flush()

    audit = AuditLog(
        id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_{stable_tx_id}",
        case_id=result.get("case_id"),
        transaction_id=stable_tx_id,
        event_type="SUSPICIOUS_ATTACK_SIMULATED",
        actor="DEMO_ATTACK_GENERATOR",
        previous_state=None,
        new_state="CRITICAL",
        api_ref="/api/demo/trigger-suspicious",
        details={"amount": 2890.00, "risk_score": 98.0, "case_id": result.get("case_id"), "idempotent": True}
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "transaction_id": stable_tx_id,
        "case_id": stable_case_id,
        "risk_level": "CRITICAL",
        "investigation_result": result
    }

@router.post("/run-investigation")
def trigger_full_investigation_run(db: Session = Depends(get_db)):
    """
    Finds the primary fraud syndicate transaction (TXN_FRAUD_901) and runs full multi-agent investigation.
    Executes idempotently without creating duplicate cases or financial operations.
    """
    txn = db.query(Transaction).filter(Transaction.id == "TXN_FRAUD_901").first()
    if not txn:
        # Fallback to any critical transaction or seed first
        txn = db.query(Transaction).filter(Transaction.risk_category == "CRITICAL").first()
    if not txn:
        # Re-seed if no data exists
        svc = SeedService(db)
        svc.seed_demo_dataset()
        txn = db.query(Transaction).filter(Transaction.id == "TXN_FRAUD_901").first()

    orchestrator = MultiAgentOrchestrator(db)
    result = orchestrator.run_investigation(transaction_id=txn.id, force_new_case=False)
    return result
