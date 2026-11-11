import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Security
from sqlalchemy.orm import Session
from app.database import get_db
from app.security.auth import verify_mutation_auth
from app.models.models import (
    InvestigationCase, Transaction, CustomerAccount, ApprovalRequest, AuditLog, PaymentOperation
)
from app.schemas.schemas import CaseDetailSchema, CaseApprovalAction
from app.agents.orchestrator import MultiAgentOrchestrator
from app.services.payment_links import find_payment_for_case
from app.services.approval_integrity import approval_integrity_state

def utcnow():
    return datetime.now(timezone.utc)

VALID_CASE_STATUSES = {
    "DETECTED", "INVESTIGATING", "PENDING_REVIEW", "APPROVED",
    "REJECTED", "ACTION_QUEUED", "ACTION_EXECUTING", "ACTION_COMPLETED",
    "ACTION_FAILED", "CLOSED"
}

ALLOWED_TRANSITIONS = {
    "DETECTED": {"INVESTIGATING", "PENDING_REVIEW", "CLOSED"},
    "INVESTIGATING": {"PENDING_REVIEW", "CLOSED", "DETECTED"},
    "PENDING_REVIEW": {"APPROVED", "REJECTED", "INVESTIGATING"},
    "APPROVED": {"ACTION_QUEUED", "ACTION_EXECUTING", "ACTION_COMPLETED", "ACTION_FAILED", "REJECTED"},
    "REJECTED": {"CLOSED", "PENDING_REVIEW"},
    "ACTION_QUEUED": {"ACTION_EXECUTING", "ACTION_FAILED"},
    "ACTION_EXECUTING": {"ACTION_COMPLETED", "ACTION_FAILED"},
    "ACTION_COMPLETED": {"CLOSED"},
    "ACTION_FAILED": {"ACTION_QUEUED", "PENDING_REVIEW", "CLOSED"},
    "CLOSED": {"INVESTIGATING", "PENDING_REVIEW"}
}

router = APIRouter(prefix="/investigations", tags=["Investigations"])


@router.get("")
def list_investigations(
    status: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(InvestigationCase)
    if status:
        query = query.filter(InvestigationCase.status == status.upper())
    if risk_level:
        query = query.filter(InvestigationCase.risk_level == risk_level.upper())
    
    cases = query.order_by(InvestigationCase.created_at.desc()).all()
    results = []
    for c in cases:
        txn = c.primary_transaction
        cust = txn.customer if txn else None
        approval_integrity_valid, approval_integrity_warning = approval_integrity_state(db, c)

        # Robust foreign key resolution without silent $0.00 or Unknown
        if txn:
            tx_amount = txn.amount
            tx_currency = txn.currency
            tx_status = txn.payment_status
            if cust:
                cust_name = cust.full_name
                cust_id = cust.id
                cust_email = cust.email
            else:
                cust_name = "MISSING_CUSTOMER_RECORD"
                cust_id = txn.customer_id
                cust_email = None
        else:
            tx_amount = None
            tx_currency = "USD"
            tx_status = "RECORD_MISSING"
            cust_name = "DATA_CORRUPTED_NO_TXN"
            cust_id = "UNKNOWN"
            cust_email = None

        results.append({
            "id": c.id,
            "primary_transaction_id": c.primary_transaction_id,
            "fraud_cluster_id": c.fraud_cluster_id,
            "related_accounts": c.related_accounts or [],
            "risk_level": c.risk_level,
            "status": c.status,
            "evidence_count": c.evidence_count,
            "assigned_investigator": c.assigned_investigator,
            "recommended_action": c.recommended_action,
            "approval_status": c.approval_status,
            "approval_integrity_valid": approval_integrity_valid,
            "approval_integrity_warning": approval_integrity_warning,
            "summary": c.summary,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
            "transaction_amount": tx_amount,
            "currency": tx_currency,
            "payment_status": tx_status,
            "customer_name": cust_name,
            "customer_id": cust_id,
            "customer_email": cust_email
        })
    return results

@router.get("/{case_id}", response_model=CaseDetailSchema)
def get_investigation_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Investigation case '{case_id}' not found")
    
    # Query linked customer and payment metadata
    txn = case.primary_transaction
    cust = txn.customer if txn else None
    
    # Query linked captured payment
    linked_payment = find_payment_for_case(db, case.id, case.primary_transaction_id)

    # Query latest approval request
    req = db.query(ApprovalRequest).filter(ApprovalRequest.case_id == case.id).order_by(ApprovalRequest.created_at.desc()).first()

    approval_integrity_valid, approval_integrity_warning = approval_integrity_state(db, case, req)

    # Only expose a scoring breakdown that was persisted by an investigation run.
    latest_ra = case.risk_assessments[-1] if case.risk_assessments else None
    if (
        latest_ra
        and isinstance(latest_ra.scoring_details, dict)
        and latest_ra.scoring_details.get("calculation_version") == "heuristic_v2"
    ):
        scoring_details = latest_ra.scoring_details
    else:
        scoring_details = {}

    # Report the local payment record only. This GET does not query PayPal.
    if linked_payment and linked_payment.capture_id:
        is_sim = linked_payment.is_simulated
        refundable_bal = 0.0 if linked_payment.refund_status == "COMPLETED" else linked_payment.amount
        refund_response = linked_payment.raw_response or {}
        recorded_refund_id = refund_response.get("id") or refund_response.get("refund_id")
        paypal_verification = {
            "capture_id": linked_payment.capture_id,
            "status": linked_payment.payment_status,
            "captured_amount": linked_payment.amount,
            "currency": linked_payment.currency,
            "refundable_balance": refundable_bal,
            "is_simulated": is_sim,
            "integration_mode": "SIMULATED_SANDBOX" if is_sim else "PAYPAL_API_RECORD_NOT_REVERIFIED",
            "verification_source": "LOCAL_SIMULATED_PAYMENT_RECORD" if is_sim else "LOCAL_PAYMENT_OPERATION_RECORD",
            "transaction_ref_matches": bool(linked_payment.transaction_ref == case.primary_transaction_id),
            "has_previous_refund": bool(linked_payment.refund_status == "COMPLETED"),
            "previous_refunds": [
                {
                    "refund_id": recorded_refund_id,
                    "amount": linked_payment.amount,
                    "currency": linked_payment.currency,
                    "status": "COMPLETED",
                    "refunded_at": linked_payment.updated_at.isoformat() if linked_payment.updated_at else None
                }
            ] if linked_payment.refund_status == "COMPLETED" else [],
            "seller_protection": "NOT_CHECKED",
            "eligible_for_refund": bool(
                linked_payment.capture_id
                and len(linked_payment.capture_id) >= 8
                and linked_payment.payment_status in ("COMPLETED", "CAPTURED")
                and linked_payment.refund_status not in ("COMPLETED", "PROCESSING")
            ),
        }
    else:
        paypal_verification = {
            "capture_id": None,
            "status": "NO_CAPTURE_RECORDED" if not linked_payment else (linked_payment.payment_status or "UNCAPTURED"),
            "captured_amount": 0.0,
            "currency": txn.currency if txn else (linked_payment.currency if linked_payment else "USD"),
            "refundable_balance": 0.0,
            "is_simulated": linked_payment.is_simulated if linked_payment else False,
            "integration_mode": "NONE" if not linked_payment else ("SIMULATED_SANDBOX" if linked_payment.is_simulated else "PAYPAL_API_RECORD_NOT_REVERIFIED"),
            "verification_source": "NO_PAYMENT_OPERATION_RECORD" if not linked_payment else "LOCAL_PAYMENT_OPERATION_WITHOUT_CAPTURE",
            "transaction_ref_matches": bool(linked_payment and linked_payment.transaction_ref == case.primary_transaction_id),
            "has_previous_refund": False,
            "previous_refunds": [],
            "seller_protection": "NOT_CHECKED_NO_CAPTURE",
            "eligible_for_refund": False,
        }

    device = txn.device if txn else None
    canonical_fingerprint = device.device_fingerprint if device else None

    # Build a timeline only from persisted records. A case read must not invent
    # completed agent stages, timestamps, reviewer decisions, or PayPal activity.
    timeline_events = []

    for execution in sorted(
        case.agent_executions,
        key=lambda item: item.started_at.isoformat() if item.started_at else "",
    ):
        summary = execution.findings or "No findings were stored for this execution."
        output_json = execution.output_json or {}
        if execution.stage == "IDENTITY_INTEL" and device and canonical_fingerprint:
            old_fingerprint = (output_json.get("findings") or {}).get("device_fingerprint")
            if old_fingerprint and old_fingerprint != canonical_fingerprint and old_fingerprint in summary:
                summary = summary.replace(old_fingerprint, canonical_fingerprint)
            if canonical_fingerprint not in summary:
                summary = f"{summary} Linked device record fingerprint: {canonical_fingerprint}."
            output_json = {
                **output_json,
                "findings": {
                    **(output_json.get("findings") or {}),
                    "device_fingerprint": canonical_fingerprint,
                },
            }
        event_time = execution.completed_at or execution.started_at
        timeline_events.append({
            "sort_time": event_time.isoformat() if event_time else "",
            "stage_name": execution.stage.replace("_", " ").title(),
            "actor": execution.agent_name,
            "status": execution.status,
            "timestamp": event_time.isoformat() if event_time else None,
            "summary": summary,
            "evidence_refs": execution.evidence_ids or [],
            "raw_data": output_json,
        })

    if req:
        request_time = req.resolved_at or req.created_at
        timeline_events.append({
            "sort_time": request_time.isoformat() if request_time else "",
            "stage_name": "Human Review",
            "actor": req.approved_by or "Reviewer name not recorded",
            "status": req.status,
            "timestamp": request_time.isoformat() if request_time else None,
            "summary": req.reason or "No reviewer reason was recorded.",
            "evidence_refs": [],
            "raw_data": {"approval_status": req.status, "approver": req.approved_by},
        })

    if linked_payment:
        payment_time = linked_payment.updated_at
        timeline_events.append({
            "sort_time": payment_time.isoformat() if payment_time else "",
            "stage_name": "Payment Operation Record",
            "actor": "Local payment ledger",
            "status": "SIMULATED_RECORD" if linked_payment.is_simulated else "LOCAL_RECORD_NOT_REVERIFIED",
            "timestamp": payment_time.isoformat() if payment_time else None,
            "summary": (
                f"Local record status: {linked_payment.payment_status}; refund status: "
                f"{linked_payment.refund_status}; capture reference: {linked_payment.capture_id or 'none'}. "
                "This case-details request did not query PayPal or execute a payment action."
            ),
            "evidence_refs": [],
            "raw_data": {"payment_id": linked_payment.id, "is_simulated": linked_payment.is_simulated},
        })

    if not timeline_events:
        timeline_events.append({
            "sort_time": case.created_at.isoformat() if case.created_at else "",
            "stage_name": "Case Record",
            "actor": "Investigation ledger",
            "status": case.status,
            "timestamp": case.created_at.isoformat() if case.created_at else None,
            "summary": case.summary or "No investigation execution or reviewer activity is recorded for this case.",
            "evidence_refs": [],
            "raw_data": {"case_id": case.id, "case_status": case.status},
        })

    timeline = []
    for index, event in enumerate(sorted(timeline_events, key=lambda item: item["sort_time"]), start=1):
        event.pop("sort_time", None)
        timeline.append({"stage_number": index, **event})

    # Format output according to schema
    case_dict = {
        "id": case.id,
        "primary_transaction_id": case.primary_transaction_id,
        "fraud_cluster_id": case.fraud_cluster_id,
        "related_accounts": case.related_accounts or [],
        "risk_level": case.risk_level,
        "status": case.status,
        "evidence_count": len(case.evidence),
        "assigned_investigator": case.assigned_investigator,
        "recommended_action": case.recommended_action,
        "approval_status": case.approval_status,
        "approval_integrity_valid": approval_integrity_valid,
        "approval_integrity_warning": approval_integrity_warning,
        "summary": case.summary,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "primary_transaction": txn,
        "customer_name": cust.full_name if cust else ("UNKNOWN_CUSTOMER" if not txn else "NO_CUSTOMER_RECORD"),
        "customer_id": cust.id if cust else (txn.customer_id if txn else None),
        "customer_email": cust.email if cust else None,
        "customer_risk_rating": cust.risk_rating if cust else "UNKNOWN",
        "transaction_amount": txn.amount if txn else None,
        "currency": txn.currency if txn else "USD",
        "payment_status": txn.payment_status if txn else "UNKNOWN",
        "paypal_eligible": bool(
            linked_payment
            and linked_payment.capture_id
            and linked_payment.payment_status in ("COMPLETED", "CAPTURED")
            and linked_payment.refund_status not in ("COMPLETED", "PROCESSING")
        ),
        "capture_id": linked_payment.capture_id if linked_payment else None,
        "financial_impact": txn.amount if txn else (linked_payment.amount if linked_payment else 0.0),
        "operation_reference": req.operation_reference if req else None,
        "approving_user": req.approved_by if (req and req.status == "APPROVED") else None,
        "approval_timestamp": req.resolved_at if (req and req.status == "APPROVED") else None,
        "evidence": case.evidence,
        "agent_executions": case.agent_executions,
        "risk_assessments": case.risk_assessments,
        "approval_requests": case.approval_requests,
        "payment_operations": case.payment_operations,
        "reasoning_timeline": timeline,
        "scoring_details": scoring_details,
        "paypal_verification": paypal_verification
    }
    return case_dict

@router.post("/{case_id}/run")
def run_case_investigation(
    case_id: str,
    db: Session = Depends(get_db),
    auth: dict = Security(verify_mutation_auth),
):
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Investigation case '{case_id}' not found")
    
    # Verify primary transaction exists before running agents
    if not case.primary_transaction:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot investigate case {case_id}: primary transaction '{case.primary_transaction_id}' is missing from database."
        )

    orchestrator = MultiAgentOrchestrator(db)
    result = orchestrator.run_investigation(transaction_id=case.primary_transaction_id, force_new_case=False)
    return result

@router.post("/{case_id}/approve", summary="Human Review: Approve Case")
def approve_case_action(
    case_id: str,
    payload: CaseApprovalAction,
    db: Session = Depends(get_db),
    auth: dict = Security(verify_mutation_auth),
):
    """
    Records the named human reviewer's approval decision for an investigation case.

    Protected by mutation authentication guard (API key or loopback-only demo).
    """
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Investigation case '{case_id}' not found")

    # Terminal or downstream state check: cannot re-approve an already executed or closed case
    if case.status in ("ACTION_COMPLETED", "CLOSED", "REJECTED"):
        db.add(AuditLog(
            id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_REJ_TRANS",
            case_id=case.id,
            transaction_id=case.primary_transaction_id,
            event_type="TRANSITION_REJECTED",
            actor=payload.investigator_name,
            previous_state=case.status,
            new_state=case.status,
            api_ref="/api/investigations/approve",
            details={
                "attempted_transition": "APPROVED",
                "current_status": case.status,
                "reason": f"Cannot transition to APPROVED from status '{case.status}'."
            }
        ))
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state transition: Cannot approve case in '{case.status}' status."
        )

    # Idempotent response for currently approved cases
    if case.status == "APPROVED":
        db.add(AuditLog(
            id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_DUP_APP",
            case_id=case.id,
            transaction_id=case.primary_transaction_id,
            event_type="DUPLICATE_APPROVAL_ATTEMPTED",
            actor=payload.investigator_name,
            previous_state=case.status,
            new_state=case.status,
            api_ref="/api/investigations/approve",
            details={"reason": payload.reason, "message": "Case was already approved; duplicate request audited."}
        ))
        db.commit()
        return {
            "status": "SUCCESS",
            "case_id": case.id,
            "approval_status": "APPROVED",
            "message": "Case was already approved."
        }

    # State Transition Check
    valid_prior_states = {"PENDING_REVIEW", "DETECTED", "INVESTIGATING", "ACTION_FAILED"}
    if case.status not in valid_prior_states:
        db.add(AuditLog(
            id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_REJ_TRANS",
            case_id=case.id,
            transaction_id=case.primary_transaction_id,
            event_type="TRANSITION_REJECTED",
            actor=payload.investigator_name,
            previous_state=case.status,
            new_state=case.status,
            api_ref="/api/investigations/approve",
            details={
                "attempted_transition": "APPROVED",
                "current_status": case.status,
                "reason": f"Cannot transition to APPROVED from status '{case.status}'."
            }
        ))
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state transition: Cannot approve case in '{case.status}' status."
        )

    op_ref = f"OP_REF_{case.id}_{uuid.uuid4().hex[:6].upper()}"
    previous_state = case.status
    case.approval_status = "APPROVED"
    case.status = "APPROVED"
    case.updated_at = utcnow()

    # Update or create approval request
    req = db.query(ApprovalRequest).filter(ApprovalRequest.case_id == case_id).order_by(ApprovalRequest.created_at.desc()).first()
    if not req:
        req = ApprovalRequest(
            id=f"REQ_{case.id}",
            case_id=case.id,
            action_type=f"EXECUTE_{case.recommended_action}",
            status="APPROVED",
            requested_by="Response Planning Agent",
            approved_by=payload.investigator_name,
            operation_reference=op_ref,
            reason=payload.reason,
            resolved_at=utcnow()
        )
        db.add(req)
    else:
        req.status = "APPROVED"
        req.approved_by = payload.investigator_name
        req.operation_reference = op_ref
        req.resolved_at = utcnow()
        req.reason = payload.reason

    # Synchronize linked Payment Operation approval status
    # Only mark payment APPROVED if it has a verified capture; uncaptured authorizations cannot be approved for refund
    linked_payment = find_payment_for_case(db, case.id, case.primary_transaction_id)
    if linked_payment:
        if linked_payment.capture_id and linked_payment.payment_status in ("COMPLETED", "CAPTURED"):
            linked_payment.approval_status = "APPROVED"
        else:
            linked_payment.approval_status = "INELIGIBLE" if linked_payment.refund_status == "INELIGIBLE" else "PENDING"
        linked_payment.updated_at = utcnow()

    # Audit Log
    audit = AuditLog(
        id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_APP_{case_id}",
        case_id=case.id,
        transaction_id=case.primary_transaction_id,
        event_type="HUMAN_APPROVAL_GRANTED",
        actor=payload.investigator_name,
        previous_state=previous_state,
        new_state="APPROVED",
        api_ref="/api/investigations/approve",
        details={
            "reason": payload.reason,
            "recommended_action": case.recommended_action,
            "operation_reference": op_ref
        }
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "case_id": case.id,
        "approval_status": "APPROVED",
        "recommended_action": case.recommended_action,
        "approved_by": payload.investigator_name,
        "operation_reference": op_ref,
        "message": f"Action {case.recommended_action} approved by {payload.investigator_name}."
    }

@router.post("/{case_id}/reject", summary="Human Review: Reject Case")
def reject_case_action(
    case_id: str,
    payload: CaseApprovalAction,
    db: Session = Depends(get_db),
    auth: dict = Security(verify_mutation_auth),
):
    """
    Records the named human reviewer's rejection decision for an investigation case.

    Protected by mutation authentication guard (API key or loopback-only demo).
    """
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Investigation case '{case_id}' not found")

    # Idempotent response for already-rejected cases
    if case.status == "REJECTED" or case.approval_status == "REJECTED":
        db.add(AuditLog(
            id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_DUP_REJ",
            case_id=case.id,
            transaction_id=case.primary_transaction_id,
            event_type="DUPLICATE_REJECTION_ATTEMPTED",
            actor=payload.investigator_name,
            previous_state=case.status,
            new_state=case.status,
            api_ref="/api/investigations/reject",
            details={"reason": payload.reason, "message": "Case was already rejected; duplicate request audited."}
        ))
        db.commit()
        return {
            "status": "SUCCESS",
            "case_id": case.id,
            "approval_status": "REJECTED",
            "rejected_by": payload.investigator_name,
            "message": "Case was already rejected."
        }

    # State Transition Check
    valid_prior_states = {"PENDING_REVIEW", "DETECTED", "INVESTIGATING", "ACTION_FAILED"}
    if case.status not in valid_prior_states:
        db.add(AuditLog(
            id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_REJ_TRANS",
            case_id=case.id,
            transaction_id=case.primary_transaction_id,
            event_type="TRANSITION_REJECTED",
            actor=payload.investigator_name,
            previous_state=case.status,
            new_state=case.status,
            api_ref="/api/investigations/reject",
            details={
                "attempted_transition": "REJECTED",
                "current_status": case.status,
                "reason": f"Cannot transition to REJECTED from status '{case.status}'."
            }
        ))
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state transition: Cannot reject case in '{case.status}' status."
        )

    previous_state = case.status
    case.approval_status = "REJECTED"
    case.status = "REJECTED"
    case.updated_at = utcnow()

    req = db.query(ApprovalRequest).filter(ApprovalRequest.case_id == case_id).order_by(ApprovalRequest.created_at.desc()).first()
    if req:
        req.status = "REJECTED"
        req.approved_by = payload.investigator_name
        req.resolved_at = utcnow()
        req.reason = payload.reason

    # Synchronize linked Payment Operation rejection
    linked_payment = find_payment_for_case(db, case.id, case.primary_transaction_id)
    if linked_payment:
        linked_payment.approval_status = "REJECTED"
        linked_payment.updated_at = utcnow()

    audit = AuditLog(
        id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_REJ_{case_id}",
        case_id=case.id,
        transaction_id=case.primary_transaction_id,
        event_type="HUMAN_APPROVAL_REJECTED",
        actor=payload.investigator_name,
        previous_state=previous_state,
        new_state="REJECTED",
        api_ref="/api/investigations/reject",
        details={"reason": payload.reason}
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "case_id": case.id,
        "approval_status": "REJECTED",
        "rejected_by": payload.investigator_name
    }
