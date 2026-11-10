from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import AuditLog
from app.schemas.schemas import AuditLogSchema

router = APIRouter(prefix="/audit", tags=["Audit"])

from sqlalchemy import or_

@router.get("", response_model=List[AuditLogSchema])
def list_audit_trail(
    event_type: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    case_id: Optional[str] = Query(None),
    transaction_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if event_type:
        query = query.filter(AuditLog.event_type == event_type.upper())
    if actor:
        query = query.filter(AuditLog.actor.ilike(f"%{actor}%"))
    if case_id:
        query = query.filter(AuditLog.case_id == case_id)
    if transaction_id:
        query = query.filter(AuditLog.transaction_id == transaction_id)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                AuditLog.id.ilike(search_term),
                AuditLog.actor.ilike(search_term),
                AuditLog.event_type.ilike(search_term),
                AuditLog.case_id.ilike(search_term),
                AuditLog.transaction_id.ilike(search_term),
                AuditLog.api_ref.ilike(search_term)
            )
        )

    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return logs
