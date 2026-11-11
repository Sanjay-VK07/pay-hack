import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Security
from sqlalchemy.orm import Session
from app.database import get_db
from app.security.auth import verify_mutation_auth
from app.models.models import Transaction, CustomerAccount, Device, PaymentIdentity, TransactionIndicator, AuditLog
from app.schemas.schemas import (
    TransactionSchema, TransactionIngestSchema, TransactionDetailSchema,
    CustomerAccountSchema, DeviceSchema, PaymentIdentitySchema, IndicatorSchema
)
from app.fraud.risk_engine import DeterministicRiskEngine
from app.agents.orchestrator import MultiAgentOrchestrator

def utcnow():
    return datetime.now(timezone.utc)

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.get("", response_model=List[TransactionSchema])
def list_transactions(
    risk_category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(Transaction).outerjoin(CustomerAccount, Transaction.customer_id == CustomerAccount.id)
    if risk_category:
        query = query.filter(Transaction.risk_category == risk_category.upper())
    if status:
        query = query.filter(Transaction.payment_status == status.upper())
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Transaction.id.ilike(search_filter)) |
            (Transaction.customer_id.ilike(search_filter)) |
            (CustomerAccount.full_name.ilike(search_filter)) |
            (CustomerAccount.account_number.ilike(search_filter)) |
            (CustomerAccount.email.ilike(search_filter)) |
            (Transaction.ip_address.ilike(search_filter))
        )

    txns = query.order_by(Transaction.timestamp.desc()).offset(offset).limit(limit).all()
    results = []
    for t in txns:
        results.append(TransactionSchema(
            id=t.id,
            customer_id=t.customer_id,
            customer_name=t.customer.full_name if t.customer else "Unknown",
            customer_email=t.customer.email if t.customer else "unknown@test.com",
            amount=t.amount,
            currency=t.currency,
            timestamp=t.timestamp,
            payment_status=t.payment_status,
            risk_score=t.risk_score,
            risk_category=t.risk_category,
            device_id=t.device_id,
            ip_address=t.ip_address,
            payment_identity_id=t.payment_identity_id,
            investigation_status=t.investigation_status,
            failure_reason=t.failure_reason,
            merchant_name=t.merchant_name
        ))
    return results

@router.get("/{transaction_id}", response_model=TransactionDetailSchema)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    t = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")

    customer_schema = None
    if t.customer:
        customer_schema = CustomerAccountSchema(
            id=t.customer.id,
            account_number=t.customer.account_number,
            full_name=t.customer.full_name,
            email=t.customer.email,
            phone=t.customer.phone,
            country=t.customer.country,
            risk_rating=t.customer.risk_rating,
            account_age_days=t.customer.account_age_days,
            status=t.customer.status
        )

    device_schema = None
    if t.device:
        device_schema = DeviceSchema(
            id=t.device.id,
            device_fingerprint=t.device.device_fingerprint,
            device_type=t.device.device_type,
            os=t.device.os,
            browser=t.device.browser,
            is_emulator=t.device.is_emulator,
            risk_level=t.device.risk_level
        )

    pid_schema = None
    if t.payment_identity:
        pid_schema = PaymentIdentitySchema(
            id=t.payment_identity.id,
            identity_type=t.payment_identity.identity_type,
            identity_hash=t.payment_identity.identity_hash,
            masked_value=t.payment_identity.masked_value,
            risk_flags=t.payment_identity.risk_flags or []
        )

    indicators_schema = [
        IndicatorSchema(
            id=ind.id,
            indicator_type=ind.indicator_type,
            indicator_value=ind.indicator_value,
            risk_weight=ind.risk_weight,
            details=ind.details or {}
        ) for ind in t.indicators
    ]

    return TransactionDetailSchema(
        id=t.id,
        customer_id=t.customer_id,
        customer_name=t.customer.full_name if t.customer else "Unknown",
        customer_email=t.customer.email if t.customer else "unknown@test.com",
        amount=t.amount,
        currency=t.currency,
        timestamp=t.timestamp,
        payment_status=t.payment_status,
        risk_score=t.risk_score,
        risk_category=t.risk_category,
        device_id=t.device_id,
        ip_address=t.ip_address,
        payment_identity_id=t.payment_identity_id,
        investigation_status=t.investigation_status,
        failure_reason=t.failure_reason,
        merchant_name=t.merchant_name,
        customer=customer_schema,
        device=device_schema,
        payment_identity=pid_schema,
        indicators=indicators_schema,
        investigations=[{"id": inv.id, "status": inv.status, "risk_level": inv.risk_level} for inv in t.investigations]
    )

@router.post("/ingest", response_model=TransactionSchema)
def ingest_transaction(
    payload: TransactionIngestSchema,
    db: Session = Depends(get_db),
    auth: dict = Security(verify_mutation_auth),
):
    tx_id = f"TXN_{uuid.uuid4().hex[:8].upper()}"

    # Handle device
    dev_id = None
    if payload.device_fingerprint:
        existing_dev = db.query(Device).filter(Device.device_fingerprint == payload.device_fingerprint).first()
        if existing_dev:
            dev_id = existing_dev.id
            existing_dev.last_seen = utcnow()
        else:
            dev_id = f"DEV_{uuid.uuid4().hex[:6].upper()}"
            new_dev = Device(
                id=dev_id,
                device_fingerprint=payload.device_fingerprint,
                device_type=payload.device_type or "DESKTOP",
                os=payload.os or "MacOS",
                browser=payload.browser or "Chrome",
                is_emulator=payload.is_emulator,
                risk_level="HIGH" if payload.is_emulator else "LOW"
            )
            db.add(new_dev)

    # Handle payment identity
    pid_id = None
    if payload.payment_identity_value:
        existing_pid = db.query(PaymentIdentity).filter(PaymentIdentity.masked_value == payload.payment_identity_value).first()
        if existing_pid:
            pid_id = existing_pid.id
        else:
            pid_id = f"PID_{uuid.uuid4().hex[:6].upper()}"
            new_pid = PaymentIdentity(
                id=pid_id,
                identity_type=payload.payment_identity_type or "CARD_HASH",
                identity_hash=f"hash_{uuid.uuid4().hex[:12]}",
                masked_value=payload.payment_identity_value
            )
            db.add(new_pid)

    txn = Transaction(
        id=tx_id,
        customer_id=payload.customer_id,
        amount=payload.amount,
        currency=payload.currency,
        timestamp=utcnow(),
        payment_status=payload.payment_status,
        device_id=dev_id,
        ip_address=payload.ip_address or "192.168.1.1",
        payment_identity_id=pid_id,
        investigation_status="NONE",
        merchant_name=payload.merchant_name
    )
    db.add(txn)
    db.flush()

    # Instant deterministic baseline evaluation
    risk_engine = DeterministicRiskEngine(db)
    assessment = risk_engine.evaluate_transaction(txn)
    txn.risk_score = assessment["risk_score"]
    txn.risk_category = assessment["risk_level"]

    # Audit log
    audit = AuditLog(
        id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{tx_id}",
        transaction_id=tx_id,
        event_type="TRANSACTION_INGESTED",
        actor="API_GATEWAY",
        previous_state=None,
        new_state=assessment["risk_level"],
        api_ref="/api/transactions/ingest",
        details={"amount": txn.amount, "currency": txn.currency, "risk_score": txn.risk_score}
    )
    db.add(audit)
    db.commit()

    return TransactionSchema(
        id=txn.id,
        customer_id=txn.customer_id,
        customer_name=txn.customer.full_name if txn.customer else "Ingested Account",
        customer_email=txn.customer.email if txn.customer else "ingested@example.com",
        amount=txn.amount,
        currency=txn.currency,
        timestamp=txn.timestamp,
        payment_status=txn.payment_status,
        risk_score=txn.risk_score,
        risk_category=txn.risk_category,
        device_id=txn.device_id,
        ip_address=txn.ip_address,
        payment_identity_id=txn.payment_identity_id,
        investigation_status=txn.investigation_status,
        merchant_name=txn.merchant_name
    )

@router.post("/{transaction_id}/analyze")
def analyze_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    auth: dict = Security(verify_mutation_auth),
):
    orchestrator = MultiAgentOrchestrator(db)
    result = orchestrator.run_investigation(transaction_id=transaction_id)
    return result
