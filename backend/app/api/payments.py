import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Security
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.security.auth import verify_mutation_auth
from app.models.models import PaymentOperation, InvestigationCase, AuditLog, Transaction
from app.schemas.schemas import PaymentOperationSchema, RefundRequestSchema, CreateOrderSchema
from app.paypal.client import PayPalClient
from app.paypal.orders import PayPalOrders
from app.paypal.refunds import PayPalRefunds
from app.paypal.simulator import PayPalSimulator
from app.services.payment_links import find_payment_for_case
from app.services.approval_integrity import approval_integrity_state

def utcnow():
    return datetime.now(timezone.utc)

def is_valid_capture_id(capture_id: Optional[str]) -> bool:
    if not capture_id:
        return False
    return len(capture_id) >= 8 and len(capture_id) <= 64


def _find_payment_identifier(db: Session, identifier: str) -> Optional[PaymentOperation]:
    payment = db.query(PaymentOperation).filter(PaymentOperation.id == identifier).first()
    if payment:
        return payment
    payment = db.query(PaymentOperation).filter(PaymentOperation.capture_id == identifier).first()
    if payment:
        return payment
    case = db.query(InvestigationCase).filter(InvestigationCase.id == identifier).first()
    if case:
        return find_payment_for_case(db, case.id, case.primary_transaction_id)
    return None

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/{payment_id}/refund/verify")
def verify_refund_status(
    payment_id: str,
    db: Session = Depends(get_db),
    auth: dict = Security(verify_mutation_auth),
):
    """Check the status of an existing live PayPal refund without issuing one."""
    payment = db.query(PaymentOperation).filter(PaymentOperation.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.refund_status == "COMPLETED":
        return {"status": "SUCCESS", "refund_status": "COMPLETED", "payment_id": payment.id}
    if payment.refund_status != "PROCESSING":
        raise HTTPException(status_code=409, detail="There is no pending refund to verify")
    if payment.is_simulated:
        raise HTTPException(status_code=409, detail="Simulated refunds do not have a PayPal status to verify")
    if not (settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET):
        raise HTTPException(status_code=503, detail="PayPal credentials are unavailable; refund remains processing")
    response = payment.raw_response or {}
    refund_id = response.get("id") or response.get("refund_id")
    if not refund_id:
        raise HTTPException(status_code=409, detail="PayPal refund reference is missing; refund remains processing")

    refund_svc = PayPalRefunds(PayPalClient())
    details, error = refund_svc.get_refund_details(refund_id)
    if error or not details:
        raise HTTPException(status_code=502, detail="PayPal refund status could not be verified; refund remains processing")
    if details.get("id") != refund_id or not details.get("status"):
        raise HTTPException(status_code=502, detail="PayPal returned unverifiable refund details; refund remains processing")
    status = details["status"].upper()
    payment.raw_response = {**response, "verified_details": details}
    case = db.query(InvestigationCase).filter(InvestigationCase.id == payment.case_id).first() if payment.case_id else None
    txn = db.query(Transaction).filter(Transaction.id == payment.transaction_ref).first()
    now = utcnow()
    if status == "COMPLETED":
        payment.refund_status = "COMPLETED"
        payment.payment_status = "REFUNDED"
        if txn:
            txn.payment_status = "REFUNDED"
            txn.investigation_status = "RESOLVED"
        if case:
            case.status = "ACTION_COMPLETED"
            case.updated_at = now
        event_type, new_state = "PAYPAL_REFUND_CONFIRMED", "REFUNDED"
    elif status in ("FAILED", "DENIED", "CANCELLED"):
        payment.refund_status = "FAILED"
        if case:
            case.status = "ACTION_FAILED"
            case.updated_at = now
        event_type, new_state = "PAYPAL_REFUND_FAILED", "FAILED"
    else:
        payment.updated_at = now
        db.commit()
        return {"status": "PENDING_CONFIRMATION", "refund_status": "PROCESSING", "payment_id": payment.id, "paypal_reference": refund_id}

    payment.updated_at = now
    db.add(AuditLog(
        id=f"AUD_{now.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_VERIFY",
        case_id=payment.case_id,
        transaction_id=payment.transaction_ref,
        event_type=event_type,
        actor="PayPal Status Verification",
        previous_state="PROCESSING",
        new_state=new_state,
        api_ref=f"/v2/payments/refunds/{refund_id}",
        details={"case_id": payment.case_id, "transaction_id": payment.transaction_ref,
                 "capture_id": payment.capture_id, "refund_id": refund_id,
                 "api_response_status": status, "timestamp": now.isoformat(),
                 "actor": "PayPal Status Verification", "amount": payment.amount,
                 "currency": payment.currency, "is_simulated": False,
                 "integration_mode": "LIVE_PAYPAL_SANDBOX"},
    ))
    db.commit()
    return {"status": "SUCCESS" if status == "COMPLETED" else "FAILED", "refund_status": payment.refund_status, "payment_id": payment.id, "paypal_reference": refund_id}

@router.get("", response_model=List[PaymentOperationSchema])
def list_payments(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(PaymentOperation)
    if status:
        query = query.filter(PaymentOperation.payment_status == status.upper())
    
    ops = query.order_by(PaymentOperation.created_at.desc()).limit(limit).all()
    return ops

@router.post("/orders/create")
def create_paypal_order(
    payload: CreateOrderSchema,
    db: Session = Depends(get_db),
    auth: dict = Security(verify_mutation_auth),
):
    """
    Creates a PayPal Sandbox Order with CAPTURE intent or clearly labeled simulator order.
    """
    has_live_creds = bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)
    idempotency_key = f"ORD_{uuid.uuid4().hex[:12]}"
    tx_ref = payload.transaction_ref or f"TXN_{uuid.uuid4().hex[:8].upper()}"
    case = None
    if payload.case_id:
        case = db.query(InvestigationCase).filter(InvestigationCase.id == payload.case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail=f"Investigation case '{payload.case_id}' not found")
        if payload.transaction_ref and payload.transaction_ref != case.primary_transaction_id:
            raise HTTPException(status_code=409, detail="Order transaction reference must match the case's primary transaction.")
        tx_ref = case.primary_transaction_id

    if has_live_creds:
        client = PayPalClient()
        orders_svc = PayPalOrders(client)
        result, err = orders_svc.create_order(
            amount=payload.amount,
            currency=payload.currency,
            reference_id=tx_ref,
            idempotency_key=idempotency_key
        )
        if err or not result:
            raise HTTPException(status_code=400, detail=f"PayPal Orders Create Error: {err}")
        order_id = result.get("id")
        is_sim = False
    else:
        simulator = PayPalSimulator()
        result = simulator.create_simulated_order(amount=payload.amount, currency=payload.currency)
        order_id = result.get("id")
        is_sim = True

    op = PaymentOperation(
        id=f"PAY_{uuid.uuid4().hex[:12].upper()}",
        case_id=payload.case_id,
        paypal_order_id=order_id,
        transaction_ref=tx_ref,
        amount=payload.amount,
        currency=payload.currency,
        payment_status="CREATED",
        refund_status="NONE",
        approval_status="PENDING",
        operation_type="PAYPAL_CHECKOUT_ORDER",
        idempotency_key=idempotency_key,
        raw_response=result,
        is_simulated=is_sim
    )
    db.add(op)
    
    # Audit log
    audit = AuditLog(
        id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_ORD",
        case_id=payload.case_id,
        transaction_id=tx_ref,
        event_type="PAYPAL_ORDER_CREATED",
        actor="PayPal Checkout Service",
        previous_state=None,
        new_state="CREATED",
        api_ref="/v2/checkout/orders",
        details={
            "order_id": order_id,
            "amount": payload.amount,
            "currency": payload.currency,
            "is_simulated": is_sim,
            "integration_mode": "LIVE_PAYPAL_SANDBOX" if not is_sim else "SIMULATED_SANDBOX"
        }
    )
    db.add(audit)
    db.commit()

    approve_url = None
    if isinstance(result, dict):
        for link in result.get("links", []):
            if isinstance(link, dict) and link.get("rel") == "approve":
                approve_url = link.get("href")

    return {
        "status": "SUCCESS",
        "payment_id": op.id,
        "paypal_order_id": order_id,
        "approve_url": approve_url,
        "transaction_ref": tx_ref,
        "amount": payload.amount,
        "currency": payload.currency,
        "is_simulated": is_sim,
        "integration_mode": "LIVE_PAYPAL_SANDBOX" if not is_sim else "SIMULATED_SANDBOX",
        "raw_response": result
    }

@router.post("/orders/{order_id}/capture")
def capture_paypal_order(
    order_id: str,
    db: Session = Depends(get_db),
    auth: dict = Security(verify_mutation_auth),
):
    """
    Captures an authorized PayPal Sandbox Order or verified simulator order.
    """
    payment = db.query(PaymentOperation).filter(PaymentOperation.paypal_order_id == order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment order '{order_id}' not found")
    if payment.payment_status in ("CAPTURED", "COMPLETED") and payment.capture_id:
        return {
            "status": "SUCCESS",
            "order_id": order_id,
            "capture_id": payment.capture_id,
            "payment_status": payment.payment_status,
            "is_simulated": payment.is_simulated,
            "integration_mode": "SIMULATED_SANDBOX" if payment.is_simulated else "LIVE_PAYPAL_SANDBOX",
            "idempotent_replay": True,
        }
    if payment.payment_status != "CREATED":
        raise HTTPException(status_code=409, detail=f"Order cannot be captured from payment status '{payment.payment_status}'.")
    if payment.approval_status != "APPROVED" or not payment.case_id:
        raise HTTPException(status_code=403, detail="Capture blocked: a linked investigation case must be approved by a reviewer first.")
    case = db.query(InvestigationCase).filter(InvestigationCase.id == payment.case_id).first()
    if not case or case.status != "APPROVED" or case.approval_status != "APPROVED":
        raise HTTPException(status_code=403, detail="Capture blocked: the linked investigation case is not approved.")
    if case.primary_transaction_id != payment.transaction_ref:
        raise HTTPException(status_code=409, detail="Capture blocked: payment transaction reference does not match the linked case.")

    # Cross-record validation
    txn = db.query(Transaction).filter(Transaction.id == payment.transaction_ref).first()
    if txn:
        if txn.currency.upper() != payment.currency.upper():
            raise HTTPException(status_code=409, detail=f"Capture blocked: Currency mismatch between transaction ({txn.currency}) and payment ({payment.currency}).")
        if abs(txn.amount - payment.amount) >= 0.005:
            raise HTTPException(status_code=409, detail=f"Capture blocked: Amount mismatch between transaction (${txn.amount:.2f}) and payment (${payment.amount:.2f}).")

    valid_integrity, integrity_warning = approval_integrity_state(db, case)
    if not valid_integrity:
        raise HTTPException(status_code=409, detail=f"Capture blocked: Record consistency check failed: {integrity_warning}")
    has_live_creds = bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)
    is_live_call = not payment.is_simulated
    if is_live_call and not has_live_creds:
        raise HTTPException(status_code=503, detail="This payment order was created for PayPal Sandbox, but credentials are unavailable; no simulator fallback was attempted.")

    idempotency_key = f"CAP_{order_id}_{uuid.uuid4().hex[:6]}"

    if is_live_call:
        client = PayPalClient()
        orders_svc = PayPalOrders(client)
        result, err = orders_svc.capture_order(order_id, idempotency_key=idempotency_key)
        if err or not result:
            raise HTTPException(status_code=400, detail=f"PayPal Order Capture Error: {err}")
        
        capture_id = None
        captures = []
        try:
            captures = result.get("purchase_units", [])[0].get("payments", {}).get("captures", [])
            if captures:
                capture_id = captures[0].get("id")
        except Exception:
            pass
        if not capture_id or result.get("status") != "COMPLETED":
            raise HTTPException(status_code=400, detail="PayPal did not confirm a completed capture with a capture reference.")

        # Verify capture details: status, amount, currency matching
        capture_obj = captures[0] if captures else {}
        if capture_obj.get("status") and capture_obj.get("status") != "COMPLETED":
            raise HTTPException(status_code=400, detail=f"PayPal capture status is '{capture_obj.get('status')}', expected 'COMPLETED'.")
        cap_amt = (capture_obj.get("amount") or {}).get("value")
        if cap_amt is not None:
            try:
                if abs(float(cap_amt) - float(payment.amount)) >= 0.005:
                    raise HTTPException(status_code=400, detail=f"Captured amount (${float(cap_amt):.2f}) does not match payment order amount (${payment.amount:.2f}).")
            except (ValueError, TypeError):
                pass
        cap_curr = (capture_obj.get("amount") or {}).get("currency_code")
        if cap_curr and cap_curr.upper() != payment.currency.upper():
            raise HTTPException(status_code=400, detail=f"Captured currency '{cap_curr}' does not match payment currency '{payment.currency}'.")
        is_sim = False
    else:
        simulator = PayPalSimulator()
        amount = payment.amount
        currency = payment.currency
        result = simulator.capture_simulated_order(order_id, amount=amount, currency=currency)
        capture_id = result.get("purchase_units", [{}])[0].get("payments", {}).get("captures", [{}])[0].get("id", f"SIM-CAP-{uuid.uuid4().hex[:8].upper()}")
        is_sim = True

    if payment:
        payment.capture_id = capture_id
        payment.payment_status = "CAPTURED"
        payment.raw_response = result
        payment.updated_at = utcnow()

    audit = AuditLog(
        id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_CAP",
        case_id=payment.case_id,
        transaction_id=payment.transaction_ref,
        event_type="PAYPAL_PAYMENT_CAPTURED",
        actor="PayPal Payment Gateway",
        previous_state="CREATED",
        new_state="CAPTURED",
        api_ref=f"/v2/checkout/orders/{order_id}/capture",
        details={
            "order_id": order_id,
            "capture_id": capture_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "is_simulated": is_sim,
            "integration_mode": "LIVE_PAYPAL_SANDBOX" if not is_sim else "SIMULATED_SANDBOX"
        }
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "order_id": order_id,
        "capture_id": capture_id,
        "payment_status": "CAPTURED",
        "is_simulated": is_sim,
        "integration_mode": "LIVE_PAYPAL_SANDBOX" if not is_sim else "SIMULATED_SANDBOX",
        "raw_response": result
    }

@router.get("/{payment_id}/verify")
def verify_payment_capture(payment_id: str, db: Session = Depends(get_db)):
    """
    Verifies PayPal Sandbox capture details, refundable balance, previous refunds,
    and distinguishes live PayPal Sandbox calls from simulated sandbox calls.
    """
    payment = _find_payment_identifier(db, payment_id)
    
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment record for identifier '{payment_id}' not found")

    if payment.payment_status not in ("COMPLETED", "CAPTURED", "REFUNDED") or not is_valid_capture_id(payment.capture_id):
        raise HTTPException(status_code=409, detail="Payment has no valid completed capture to verify.")

    has_live_creds = bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)
    is_live_call = not payment.is_simulated
    if is_live_call and not has_live_creds:
        raise HTTPException(status_code=503, detail="This capture requires PayPal Sandbox verification, but credentials are unavailable.")

    raw_details = {}

    if is_live_call:
        client = PayPalClient()
        refund_svc = PayPalRefunds(client)
        capture, err = refund_svc.get_capture_details(payment.capture_id)
        if not err and capture:
            raw_details = capture
            integration_mode = "LIVE_PAYPAL_SANDBOX"
            is_sim = False
        else:
            raw_details = {"warning": f"Could not reach live Sandbox: {err}", "cached_status": payment.payment_status}
            integration_mode = "LIVE_PAYPAL_SANDBOX_UNREACHABLE"
            is_sim = False
    else:
        simulator = PayPalSimulator()
        raw_details = simulator.get_simulated_capture(payment.capture_id, payment.amount, payment.currency)
        integration_mode = "SIMULATED_SANDBOX"
        is_sim = True

    verified_capture_status = raw_details.get("status") or payment.payment_status
    remote_amount = (raw_details.get("amount") or {}).get("value")
    remote_currency = (raw_details.get("amount") or {}).get("currency_code")
    amount_matches = True
    currency_matches = True
    if remote_amount is not None:
        try:
            amount_matches = abs(float(remote_amount) - float(payment.amount)) < 0.005
        except (TypeError, ValueError):
            amount_matches = False
    if remote_currency:
        currency_matches = remote_currency == payment.currency
    capture_id_matches = (
        raw_details.get("id") == payment.capture_id
        if is_live_call
        else raw_details.get("id") in (None, payment.capture_id)
    )
    capture_verified = (
        integration_mode != "LIVE_PAYPAL_SANDBOX_UNREACHABLE"
        and verified_capture_status == "COMPLETED"
        and amount_matches
        and currency_matches
        and capture_id_matches
    )
    refundable_balance = (
        payment.amount
        if capture_verified and payment.refund_status not in ("COMPLETED", "PROCESSING")
        else 0.0
    )

    # Check for previous refunds
    previous_refunds = []
    if payment.refund_status == "COMPLETED":
        previous_refunds.append({
            "refund_id": payment.raw_response.get("id") or payment.raw_response.get("refund_id"),
            "amount": payment.amount,
            "currency": payment.currency,
            "status": "COMPLETED",
            "refunded_at": payment.updated_at.isoformat() if payment.updated_at else None
        })

    return {
        "payment_id": payment.id,
        "capture_id": payment.capture_id,
        "transaction_ref": payment.transaction_ref,
        "case_id": payment.case_id,
        "payment_status": payment.payment_status,
        "refund_status": payment.refund_status,
        "approval_status": payment.approval_status,
        "captured_amount": payment.amount,
        "currency": payment.currency,
        "refundable_balance": refundable_balance,
        "is_simulated": is_sim,
        "integration_mode": integration_mode,
        "verification_source": "PAYPAL_SANDBOX_V2_PAYMENTS_CAPTURES" if not is_sim else "PAYPAL_SANDBOX_SIMULATOR_TELEMETRY",
        "seller_protection": "ELIGIBLE" if capture_verified else "UNVERIFIED",
        "capture_status": verified_capture_status,
        "capture_amount_matches": amount_matches,
        "capture_currency_matches": currency_matches,
        "capture_id_matches": capture_id_matches,
        "capture_verified": capture_verified,
        "eligible_for_refund": capture_verified and payment.refund_status not in ("COMPLETED", "PROCESSING"),
        "has_previous_refund": len(previous_refunds) > 0,
        "previous_refunds": previous_refunds,
        "raw_details": raw_details,
        "verified_at": utcnow().isoformat()
    }

@router.post("/{payment_id}/refund", summary="Execute Refund (Human-approved, loopback-only)")
def execute_refund(
    payment_id: str,
    payload: RefundRequestSchema,
    db: Session = Depends(get_db),
    auth: dict = Security(verify_mutation_auth),
):
    """
    Executes an idempotent refund for a captured PayPal payment that has
    received explicit human approval in the Investigation Workspace.

    Protected by mutation authentication guard (API key or loopback-only demo).
    """
    # Step 1: Verify that the PayPal payment exists
    payment = db.query(PaymentOperation).filter(PaymentOperation.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment record '{payment_id}' not found")

    # Safety Check: Prevent duplicate refunds (Idempotent response)
    if payment.refund_status == "COMPLETED":
        return {
            "status": "ALREADY_REFUNDED",
            "refund_status": "COMPLETED",
            "payment_id": payment.id,
            "message": "Payment has already been successfully refunded.",
            "is_simulated": payment.is_simulated,
            "amount": payment.amount,
            "currency": payment.currency
        }
    if payment.refund_status == "PROCESSING":
        raise HTTPException(status_code=409, detail="Refund blocked: This payment already has a refund in progress.")

    # Step 2: Verify that the payment was captured
    if payment.payment_status not in ("COMPLETED", "CAPTURED"):
        raise HTTPException(
            status_code=400,
            detail=f"Refund rejected: Payment status is '{payment.payment_status}'. Only COMPLETED or CAPTURED payments are eligible for refund."
        )

    # Step 3: Retrieve and verify actual capture ID
    if not payment.capture_id:
        raise HTTPException(
            status_code=400,
            detail=f"Refund rejected: Payment {payment_id} does not have a verified PayPal capture ID."
        )

    if not is_valid_capture_id(payment.capture_id):
        raise HTTPException(status_code=400, detail="Refund rejected: The recorded capture reference is malformed.")

    # Step 4: Verify the refundable amount and currency
    refund_amount = payload.amount if (payload and payload.amount is not None) else payment.amount
    if refund_amount <= 0 or refund_amount > payment.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid refund amount: ${refund_amount:.2f}. Must be between $0.01 and the captured total (${payment.amount:.2f})."
        )
    if payload and payload.currency and payload.currency.upper() != payment.currency.upper():
        raise HTTPException(
            status_code=400,
            detail=f"Refund currency '{payload.currency}' does not match payment currency '{payment.currency}'."
        )

    # Step 5: Verify explicit Human Approval Gate
    if payment.approval_status == "REJECTED":
        raise HTTPException(
            status_code=403,
            detail="Refund blocked: Human investigator explicitly rejected financial remediation for this operation."
        )

    if not payment.case_id:
        raise HTTPException(
            status_code=403,
            detail="Refund blocked: Payment operation is not linked to an investigation case."
        )
    case = db.query(InvestigationCase).filter(InvestigationCase.id == payment.case_id).first()
    if not case or case.status not in ("APPROVED", "ACTION_QUEUED", "ACTION_EXECUTING") or case.approval_status != "APPROVED":
        raise HTTPException(
            status_code=403,
            detail=f"Refund blocked: Investigation case {payment.case_id} requires explicit human approval before financial reversal."
        )
    if case.primary_transaction_id != payment.transaction_ref:
        raise HTTPException(status_code=409, detail="Refund blocked: Payment transaction reference does not match the investigation case.")
    if payment.approval_status != "APPROVED":
        raise HTTPException(status_code=403, detail="Refund blocked: Payment operation has no explicit human approval.")

    # Step 6: Verify cross-record consistency between Transaction, Case, and Payment
    txn = db.query(Transaction).filter(Transaction.id == payment.transaction_ref).first()
    if txn:
        if txn.currency.upper() != payment.currency.upper():
            raise HTTPException(status_code=409, detail=f"Refund rejected: Currency mismatch between transaction ({txn.currency}) and payment ({payment.currency}).")
        if abs(txn.amount - payment.amount) >= 0.005:
            raise HTTPException(status_code=409, detail=f"Refund rejected: Amount mismatch between transaction (${txn.amount:.2f}) and payment (${payment.amount:.2f}).")
        if txn.payment_status not in ("COMPLETED", "CAPTURED"):
            raise HTTPException(status_code=409, detail=f"Refund rejected: Transaction status is '{txn.payment_status}', expected COMPLETED or CAPTURED.")

    valid_integrity, integrity_warning = approval_integrity_state(db, case)
    if not valid_integrity:
        raise HTTPException(status_code=409, detail=f"Refund rejected: Record consistency check failed: {integrity_warning}")

    has_live_creds = bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)
    is_live_call = not payment.is_simulated
    if is_live_call and not has_live_creds:
        raise HTTPException(status_code=503, detail="This capture requires PayPal Sandbox execution, but credentials are unavailable; no simulator fallback was attempted.")

    # Atomically claim this operation before calling any gateway. Concurrent retry
    # requests cannot both pass the eligibility check and submit a refund.
    claimed = db.query(PaymentOperation).filter(
        PaymentOperation.id == payment.id,
        or_(
            PaymentOperation.refund_status.is_(None),
            PaymentOperation.refund_status.notin_(("COMPLETED", "PROCESSING")),
        ),
    ).update({PaymentOperation.refund_status: "PROCESSING"}, synchronize_session=False)
    if claimed != 1:
        db.rollback()
        db.refresh(payment)
        if payment.refund_status == "COMPLETED":
            return {
                "status": "ALREADY_REFUNDED",
                "refund_status": "COMPLETED",
                "payment_id": payment.id,
                "message": "Payment has already been successfully refunded.",
                "is_simulated": payment.is_simulated,
                "amount": payment.amount,
                "currency": payment.currency,
            }
        raise HTTPException(status_code=409, detail="Refund blocked: This payment already has a refund in progress.")
    db.commit()
    db.refresh(payment)
    if case:
        case.status = "ACTION_EXECUTING"
        db.commit()

    investigator = payload.investigator
    reason = payload.reason

    # Step 7: Execute supported Sandbox refund API or verified simulator
    idempotency_key = f"REF_{payment.id}_{refund_amount:.2f}"

    if is_live_call:
        # Step 7a: Record PAYPAL_REFUND_REQUESTED before invoking external PayPal endpoint
        req_audit = AuditLog(
            id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_REQ",
            case_id=payment.case_id,
            transaction_id=payment.transaction_ref,
            event_type="PAYPAL_REFUND_REQUESTED",
            actor=investigator,
            previous_state=payment.payment_status,
            new_state="REFUND_PENDING",
            api_ref=f"/v2/payments/captures/{payment.capture_id}/refund",
            details={
                "case_id": payment.case_id,
                "transaction_id": payment.transaction_ref,
                "capture_id": payment.capture_id,
                "refund_id": None,
                "api_response_status": "REQUESTED",
                "timestamp": utcnow().isoformat(),
                "actor": investigator,
                "amount": refund_amount,
                "currency": payment.currency,
                "idempotency_key": idempotency_key,
                "reason": reason
            }
        )
        db.add(req_audit)
        db.commit()

        client = PayPalClient()
        refund_svc = PayPalRefunds(client)

        # 1. Retrieve the actual capture from PayPal
        capture_data, cap_err = refund_svc.get_capture_details(payment.capture_id)
        if cap_err or not capture_data:
            payment.refund_status = "FAILED"
            fail_audit = AuditLog(
                id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_FAIL",
                case_id=payment.case_id,
                transaction_id=payment.transaction_ref,
                event_type="PAYPAL_REFUND_FAILED",
                actor=investigator,
                previous_state="CAPTURED",
                new_state="FAILED",
                api_ref=f"/v2/payments/captures/{payment.capture_id}",
                details={
                    "case_id": payment.case_id,
                    "transaction_id": payment.transaction_ref,
                    "capture_id": payment.capture_id,
                    "refund_id": None,
                    "api_response_status": "FAILED",
                    "timestamp": utcnow().isoformat(),
                    "actor": investigator,
                    "error": cap_err or "Failed to retrieve capture from PayPal Sandbox"
                }
            )
            db.add(fail_audit)
            if case:
                case.status = "ACTION_FAILED"
            db.commit()
            raise HTTPException(status_code=400, detail=f"PayPal Capture Verification Failed: {cap_err}")

        # 2. Verify capture status
        capture_amount_data = capture_data.get("amount") or {}
        capture_amount_valid = True
        if capture_amount_data.get("value") is not None:
            try:
                capture_amount_valid = abs(float(capture_amount_data["value"]) - float(payment.amount)) < 0.005
            except (TypeError, ValueError):
                capture_amount_valid = False
        capture_currency_valid = not capture_amount_data.get("currency_code") or capture_amount_data.get("currency_code") == payment.currency
        capture_identity_valid = capture_data.get("id") == payment.capture_id
        if (
            capture_data.get("status") != "COMPLETED"
            or not capture_amount_valid
            or not capture_currency_valid
            or not capture_identity_valid
        ):
            payment.refund_status = "FAILED"
            if case:
                case.status = "ACTION_FAILED"
            db.add(AuditLog(
                id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_FAIL",
                case_id=payment.case_id,
                transaction_id=payment.transaction_ref,
                event_type="PAYPAL_REFUND_FAILED",
                actor=investigator if 'investigator' in locals() else "Refund Validator",
                previous_state=payment.payment_status,
                new_state="FAILED",
                api_ref=f"/v2/payments/captures/{payment.capture_id}",
                details={
                    "case_id": payment.case_id,
                    "transaction_id": payment.transaction_ref,
                    "capture_id": payment.capture_id,
                    "refund_id": None,
                    "api_response_status": "CAPTURE_VALIDATION_FAILED",
                    "timestamp": utcnow().isoformat(),
                    "capture_status": capture_data.get("status"),
                    "capture_amount_matches": capture_amount_valid,
                    "capture_currency_matches": capture_currency_valid,
                    "capture_id_matches": capture_identity_valid,
                },
            ))
            db.commit()
            raise HTTPException(status_code=400, detail="PayPal capture verification failed: status, identity, amount, or currency did not match the payment record.")

        # 7b. Execute refund using PayPal actual API
        result, err = refund_svc.refund_capture(
            capture_id=payment.capture_id,
            amount=refund_amount,
            currency=payment.currency,
            note_to_payer=reason,
            idempotency_key=idempotency_key
        )

        if err or not result:
            payment.refund_status = "FAILED"
            payment.raw_response = {"error": err}
            if case:
                case.status = "ACTION_FAILED"
            fail_audit = AuditLog(
                id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_FAIL",
                case_id=payment.case_id,
                transaction_id=payment.transaction_ref,
                event_type="PAYPAL_REFUND_FAILED",
                actor=investigator,
                previous_state="CAPTURED",
                new_state="FAILED",
                api_ref=f"/v2/payments/captures/{payment.capture_id}/refund",
                details={
                    "case_id": payment.case_id,
                    "transaction_id": payment.transaction_ref,
                    "capture_id": payment.capture_id,
                    "refund_id": None,
                    "api_response_status": "FAILED",
                    "timestamp": utcnow().isoformat(),
                    "actor": investigator,
                    "error": err
                }
            )
            db.add(fail_audit)
            db.commit()
            raise HTTPException(status_code=400, detail=f"PayPal Refund Error: {err}")

        # Confirm only a completed refund with a concrete provider reference.
        paypal_refund_id = result.get("id")
        api_status = result.get("status")
        refund_confirmed = bool(paypal_refund_id and api_status == "COMPLETED")
        verified_details = None
        if paypal_refund_id:
            verify_refund, _ = refund_svc.get_refund_details(paypal_refund_id)
            if verify_refund and "status" in verify_refund:
                api_status = verify_refund["status"]
                verified_details = verify_refund
                refund_confirmed = api_status == "COMPLETED"

        payment.raw_response = {**result, **({"verified_details": verified_details} if verified_details else {})}
        payment.is_simulated = False
        if api_status in ("FAILED", "DENIED", "CANCELLED"):
            payment.refund_status = "FAILED"
            payment.updated_at = utcnow()
            if case:
                case.status = "ACTION_FAILED"
            db.add(AuditLog(
                id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_FAIL",
                case_id=payment.case_id,
                transaction_id=payment.transaction_ref,
                event_type="PAYPAL_REFUND_FAILED",
                actor=investigator,
                previous_state=payment.payment_status,
                new_state="FAILED",
                api_ref=f"/v2/payments/refunds/{paypal_refund_id or 'unverified'}",
                details={
                    "case_id": payment.case_id,
                    "transaction_id": payment.transaction_ref,
                    "capture_id": payment.capture_id,
                    "refund_id": paypal_refund_id,
                    "api_response_status": api_status,
                    "timestamp": utcnow().isoformat(),
                    "actor": investigator,
                    "amount": refund_amount,
                    "currency": payment.currency,
                    "integration_mode": "LIVE_PAYPAL_SANDBOX",
                },
            ))
            db.commit()
            raise HTTPException(status_code=400, detail=f"PayPal reported refund status {api_status}.")
        if not refund_confirmed:
            payment.refund_status = "PROCESSING"
            payment.updated_at = utcnow()
            db.add(AuditLog(
                id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_PENDING",
                case_id=payment.case_id,
                transaction_id=payment.transaction_ref,
                event_type="PAYPAL_REFUND_PENDING",
                actor=investigator,
                previous_state=payment.payment_status,
                new_state="PROCESSING",
                api_ref=f"/v2/payments/refunds/{paypal_refund_id or 'unverified'}",
                details={
                    "case_id": payment.case_id,
                    "transaction_id": payment.transaction_ref,
                    "capture_id": payment.capture_id,
                    "refund_id": paypal_refund_id,
                    "api_response_status": api_status or "UNVERIFIED",
                    "timestamp": utcnow().isoformat(),
                    "actor": investigator,
                    "amount": refund_amount,
                    "currency": payment.currency,
                    "integration_mode": "LIVE_PAYPAL_SANDBOX",
                },
            ))
            db.commit()
            return {
                "status": "PENDING_CONFIRMATION",
                "refund_status": "PROCESSING",
                "payment_id": payment.id,
                "capture_id": payment.capture_id,
                "paypal_reference": paypal_refund_id,
                "amount": refund_amount,
                "currency": payment.currency,
                "is_simulated": False,
                "message": "PayPal has not confirmed a completed refund. The payment remains locked against duplicate requests.",
            }

        payment.refund_status = "COMPLETED"
        payment.payment_status = "REFUNDED"
        paypal_ref = paypal_refund_id

        paypal_ref = paypal_refund_id

        # Record PAYPAL_REFUND_CONFIRMED (ONLY after live PayPal Sandbox response verified)
        conf_audit = AuditLog(
            id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_CONF",
            case_id=payment.case_id,
            transaction_id=payment.transaction_ref,
            event_type="PAYPAL_REFUND_CONFIRMED",
            actor=investigator,
            previous_state="CAPTURED",
            new_state="REFUNDED",
            api_ref=f"/v2/payments/refunds/{paypal_ref}",
            details={
                "case_id": payment.case_id,
                "transaction_id": payment.transaction_ref,
                "capture_id": payment.capture_id,
                "refund_id": paypal_ref,
                "api_response_status": api_status,
                "timestamp": utcnow().isoformat(),
                "actor": investigator,
                "amount": refund_amount,
                "currency": payment.currency,
                "is_simulated": False,
                "integration_mode": "LIVE_PAYPAL_SANDBOX",
                "reason": reason
            }
        )
        db.add(conf_audit)
    else:
        # Step 7 (Simulator Fallback with transparent truthful labeling)
        simulator = PayPalSimulator()
        result = simulator.refund_simulated_capture(
            capture_id=payment.capture_id,
            amount=refund_amount,
            currency=payment.currency,
            note_to_payer=reason
        )
        payment.refund_status = "COMPLETED"
        payment.payment_status = "REFUNDED"
        payment.raw_response = result
        payment.is_simulated = True
        paypal_ref = result.get("refund_id", f"SIM-REF-{payment.capture_id}")

        # Record SIMULATED_REFUND_EXECUTED
        sim_audit = AuditLog(
            id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_SIM_REF",
            case_id=payment.case_id,
            transaction_id=payment.transaction_ref,
            event_type="SIMULATED_REFUND_EXECUTED",
            actor=investigator,
            previous_state="CAPTURED",
            new_state="REFUNDED",
            api_ref=f"/simulator/payments/captures/{payment.capture_id}/refund",
            details={
                "case_id": payment.case_id,
                "transaction_id": payment.transaction_ref,
                "capture_id": payment.capture_id,
                "refund_id": paypal_ref,
                "api_response_status": "SIMULATED_COMPLETED",
                "timestamp": utcnow().isoformat(),
                "actor": investigator,
                "amount": refund_amount,
                "currency": payment.currency,
                "is_simulated": True,
                "integration_mode": "SIMULATED_SANDBOX",
                "reason": reason
            }
        )
        db.add(sim_audit)

    payment.updated_at = utcnow()

    # Update associated transaction status
    txn = db.query(Transaction).filter(Transaction.id == payment.transaction_ref).first()
    if txn:
        txn.payment_status = "REFUNDED"
        txn.investigation_status = "RESOLVED"

    # Update case status to ACTION_COMPLETED
    if case:
        case.status = "ACTION_COMPLETED"
        case.updated_at = utcnow()

    db.commit()

    return {
        "status": "SUCCESS",
        "refund_status": "COMPLETED",
        "payment_id": payment.id,
        "capture_id": payment.capture_id,
        "paypal_reference": paypal_ref,
        "amount": refund_amount,
        "currency": payment.currency,
        "is_simulated": payment.is_simulated,
        "case_status": case.status if case else "RESOLVED",
        "message": f"Successfully refunded ${refund_amount:.2f} via {'PayPal Sandbox' if not payment.is_simulated else 'Verified Sandbox Simulator'}."
    }
