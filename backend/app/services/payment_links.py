from typing import Optional

from sqlalchemy import and_, case as sql_case, or_
from sqlalchemy.orm import Session

from app.models.models import PaymentOperation


def find_payment_for_case(
    db: Session, case_id: str, transaction_id: Optional[str]
) -> Optional[PaymentOperation]:
    """Return the newest payment operation tied to the case's primary transaction.

    Exact transaction references take precedence. A case foreign key is a fallback
    only when the payment has no transaction reference; it must never make a payment
    for another transaction appear in this case's dossier.
    """
    if not transaction_id:
        return db.query(PaymentOperation).filter(
            PaymentOperation.case_id == case_id,
            PaymentOperation.transaction_ref.is_(None),
        ).order_by(PaymentOperation.created_at.desc()).first()

    candidates = db.query(PaymentOperation).filter(
        or_(
            PaymentOperation.transaction_ref == transaction_id,
            and_(
                PaymentOperation.case_id == case_id,
                PaymentOperation.transaction_ref.is_(None),
            ),
        )
    )
    has_verified_capture = and_(
        PaymentOperation.payment_status.in_(("COMPLETED", "CAPTURED", "REFUNDED")),
        PaymentOperation.capture_id.is_not(None),
    )
    return candidates.order_by(
        sql_case((PaymentOperation.transaction_ref == transaction_id, 0), else_=1),
        sql_case((has_verified_capture, 0), else_=1),
        PaymentOperation.created_at.desc(),
    ).first()
