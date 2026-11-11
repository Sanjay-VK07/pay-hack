from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.models import ApprovalRequest, AuditLog, InvestigationCase
from app.services.payment_links import find_payment_for_case


def approval_integrity_state(
    db: Session,
    case: InvestigationCase,
    approval_request: Optional[ApprovalRequest] = None,
) -> Tuple[bool, Optional[str]]:
    """Check relational consistency between case, approval request, audit log, and payment operation.

    Validates:
    1. Approved case integrity: approved cases must have an ApprovalRequest record with
       approver and operation reference, plus a corresponding HUMAN_APPROVAL_GRANTED audit log.
    2. Cross-record consistency: flags state mismatches where a linked payment operation
       is marked APPROVED while the case is PENDING, or where an uncaptured payment has no
       capture ID yet is marked APPROVED, or where transaction and payment settlement conflict.
    """
    # Cross-record check with linked payment operation
    linked_payment = find_payment_for_case(db, case.id, case.primary_transaction_id)
    if linked_payment:
        # Check 1: Payment operation is marked APPROVED but the case is NOT approved
        if linked_payment.approval_status == "APPROVED" and (
            case.status != "APPROVED" or case.approval_status != "APPROVED"
        ):
            return False, (
                f"Legacy state mismatch: Linked payment operation {linked_payment.id} is marked APPROVED, "
                f"but investigation case {case.id} is in status '{case.status}' with approval_status='{case.approval_status}'. "
                "Financial remediation actions are blocked until explicit case review is completed."
            )

        # Check 2: Payment operation has no capture ID (UNCAPTURED) but is marked APPROVED
        if (linked_payment.payment_status == "UNCAPTURED" or not linked_payment.capture_id) and linked_payment.approval_status == "APPROVED":
            return False, (
                f"Legacy record inconsistency: Payment operation {linked_payment.id} has approval_status='APPROVED' "
                f"but has no PayPal capture ID (status: UNCAPTURED, refund: {linked_payment.refund_status}). "
                "Financial reversal is blocked: uncaptured authorizations have no settled PayPal capture to refund."
            )

        # Check 3: Transaction is COMPLETED but payment is UNCAPTURED without capture ID
        txn = case.primary_transaction
        if txn and txn.payment_status == "COMPLETED" and linked_payment.payment_status == "UNCAPTURED":
            if linked_payment.approval_status == "APPROVED" or not linked_payment.capture_id:
                return False, (
                    f"Legacy record inconsistency: Transaction {case.primary_transaction_id} is marked COMPLETED "
                    f"while payment operation {linked_payment.id} is UNCAPTURED with no capture ID and marked {linked_payment.approval_status}. "
                    "Case review remains pending; all financial remediation actions are blocked for this record."
                )

    # Check 4: If case is marked APPROVED, verify backing approval request and audit record
    if case.status != "APPROVED" and case.approval_status != "APPROVED":
        return True, None

    request = approval_request or (
        db.query(ApprovalRequest)
        .filter(ApprovalRequest.case_id == case.id)
        .order_by(ApprovalRequest.created_at.desc())
        .first()
    )
    approval_event = db.query(AuditLog).filter(
        AuditLog.case_id == case.id,
        AuditLog.event_type == "HUMAN_APPROVAL_GRANTED",
        AuditLog.new_state == "APPROVED",
    ).first()
    request_is_complete = bool(
        request
        and request.status == "APPROVED"
        and request.approved_by
        and request.operation_reference
    )
    valid = request_is_complete and approval_event is not None
    warning = None if valid else (
        "Approval status cannot be verified: the case is marked approved, but its approval request "
        "or HUMAN_APPROVAL_GRANTED audit record is missing or incomplete. Review the audit trail "
        "before any financial action."
    )
    return valid, warning
