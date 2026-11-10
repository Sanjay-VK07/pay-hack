from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import AgentExecution
from app.schemas.schemas import AgentExecutionSchema

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.get("/executions", response_model=List[AgentExecutionSchema])
def list_agent_executions(
    case_id: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(AgentExecution)
    if case_id:
        query = query.filter(AgentExecution.case_id == case_id)
    if stage:
        query = query.filter(AgentExecution.stage == stage)

    executions = query.order_by(AgentExecution.started_at.desc()).limit(limit).all()
    return executions
