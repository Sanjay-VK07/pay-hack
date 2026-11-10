from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import ApprovalRequest, AuditLog, InvestigationCase


def approval_integrity_state(
    db: Session,
    case: InvestigationCase,
    approval_request: Optional[ApprovalRequest] = None,
):
    """Report whether an approved case is backed by its request and audit event."""
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
