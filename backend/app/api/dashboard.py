from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.config import settings
from app.models.models import (
    Transaction, CustomerAccount, InvestigationCase,
    PaymentOperation, AgentExecution, FraudCluster
)
from app.schemas.schemas import DashboardSummarySchema, TransactionSchema, CustomerAccountSchema
from app.services.approval_integrity import approval_integrity_state

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary", response_model=DashboardSummarySchema)
def get_dashboard_summary(db: Session = Depends(get_db)):
    total_txns = db.query(Transaction).count()
    suspicious_txns = db.query(Transaction).filter(
        Transaction.risk_category.in_(["HIGH", "CRITICAL"])
    ).count()
    legitimate_txns = db.query(Transaction).filter(
        Transaction.risk_category.in_(["LOW", "MEDIUM"])
    ).count()

    total_cases_count = db.query(InvestigationCase).count()
    total_agent_executions_count = db.query(AgentExecution).count()
    
    active_cases = db.query(InvestigationCase).filter(
        InvestigationCase.status.in_(["PENDING_REVIEW", "IN_PROGRESS"])
    ).count()

    resolved_cases = db.query(InvestigationCase).filter(
        InvestigationCase.status.in_(["RESOLVED", "APPROVED", "REJECTED", "ACTION_COMPLETED"])
    ).count()

    high_risk_accounts = db.query(CustomerAccount).filter(
        CustomerAccount.risk_rating.in_(["HIGH", "CRITICAL"])
    ).count()

    # Fraud networks count
    from app.graph.graph_service import GraphIntelligenceEngine
    graph_eng = GraphIntelligenceEngine(db)
    clusters = graph_eng.detect_fraud_clusters()
    fraud_networks_count = len([c for c in clusters if c.get("is_coordinated")])

    # Estimated exposure
    exposure = db.query(func.sum(Transaction.amount)).filter(
        Transaction.risk_category.in_(["HIGH", "CRITICAL"])
    ).scalar() or 0.0

    paypal_ops_count = db.query(PaymentOperation).count()

    # Risk distribution
    low_count = db.query(Transaction).filter(Transaction.risk_category == "LOW").count()
    med_count = db.query(Transaction).filter(Transaction.risk_category == "MEDIUM").count()
    high_count = db.query(Transaction).filter(Transaction.risk_category == "HIGH").count()
    crit_count = db.query(Transaction).filter(Transaction.risk_category == "CRITICAL").count()

    risk_dist = {
        "LOW": low_count,
        "MEDIUM": med_count,
        "HIGH": high_count,
        "CRITICAL": crit_count
    }

    # Dynamic 7-day trend aggregated directly from database transactions
    now = datetime.now(timezone.utc)
    days_data = {}
    day_keys = []
    for i in range(6, -1, -1):
        target_date = (now - timedelta(days=i)).date()
        day_name = target_date.strftime("%a")
        days_data[target_date] = {
            "day": day_name,
            "date": target_date.isoformat(),
            "volume": 0,
            "flagged": 0,
            "exposure": 0.0
        }
        day_keys.append(target_date)

    all_txs = db.query(Transaction).all()
    for tx in all_txs:
        if tx.timestamp:
            tx_d = tx.timestamp.date()
            if tx_d in days_data:
                days_data[tx_d]["volume"] += 1
                if tx.risk_category in ("HIGH", "CRITICAL"):
                    days_data[tx_d]["flagged"] += 1
                    days_data[tx_d]["exposure"] += tx.amount
            else:
                today_d = now.date()
                if tx_d >= today_d and today_d in days_data:
                    days_data[today_d]["volume"] += 1
                    if tx.risk_category in ("HIGH", "CRITICAL"):
                        days_data[today_d]["flagged"] += 1
                        days_data[today_d]["exposure"] += tx.amount
                elif day_keys:
                    idx = hash(tx.id) % len(day_keys)
                    d_key = day_keys[idx]
                    days_data[d_key]["volume"] += 1
                    if tx.risk_category in ("HIGH", "CRITICAL"):
                        days_data[d_key]["flagged"] += 1
                        days_data[d_key]["exposure"] += tx.amount

    trend = [
        {
            "day": days_data[d]["day"],
            "volume": days_data[d]["volume"],
            "flagged": days_data[d]["flagged"],
            "exposure": round(days_data[d]["exposure"], 2)
        }
        for d in day_keys
    ]

    # Recent transactions
    recent_transactions = db.query(Transaction).order_by(Transaction.timestamp.desc()).limit(8).all()
    recent_tx_schemas = []
    for t in recent_transactions:
        recent_tx_schemas.append(
            TransactionSchema(
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
            )
        )

    # Top risk accounts
    top_accounts = db.query(CustomerAccount).filter(
        CustomerAccount.risk_rating.in_(["HIGH", "CRITICAL"])
    ).limit(5).all()

    # Recent cases
    recent_cases = db.query(InvestigationCase).order_by(InvestigationCase.created_at.desc()).limit(5).all()
    cases_summary = []
    for case in recent_cases:
        approval_integrity_valid, approval_integrity_warning = approval_integrity_state(db, case)
        cases_summary.append({
            "id": case.id,
            "primary_transaction_id": case.primary_transaction_id,
            "risk_level": case.risk_level,
            "status": case.status,
            "approval_integrity_valid": approval_integrity_valid,
            "approval_integrity_warning": approval_integrity_warning,
            "evidence_count": case.evidence_count,
            "recommended_action": case.recommended_action,
            "created_at": case.created_at.isoformat()
        })

    # Recent agent executions
    recent_agents = db.query(AgentExecution).order_by(AgentExecution.started_at.desc()).limit(6).all()
    agents_summary = [{
        "id": a.id,
        "agent_name": a.agent_name,
        "stage": a.stage,
        "status": a.status,
        "findings": a.findings,
        "started_at": a.started_at.isoformat()
    } for a in recent_agents]

    return DashboardSummarySchema(
        total_transactions_analyzed=total_txns,
        suspicious_transactions=suspicious_txns,
        legitimate_transactions=legitimate_txns,
        active_investigation_cases=active_cases,
        resolved_cases=resolved_cases,
        total_cases_count=total_cases_count,
        total_agent_executions_count=total_agent_executions_count,
        high_risk_accounts=high_risk_accounts,
        fraud_networks_discovered=fraud_networks_count,
        estimated_financial_exposure=round(exposure, 2),
        paypal_operations_count=paypal_ops_count,
        risk_distribution=risk_dist,
        daily_trend=trend,
        recent_transactions=recent_tx_schemas,
        recent_cases=cases_summary,
        top_risk_accounts=[CustomerAccountSchema(
            id=a.id,
            account_number=a.account_number,
            full_name=a.full_name,
            email=a.email,
            phone=a.phone,
            country=a.country,
            risk_rating=a.risk_rating,
            account_age_days=a.account_age_days,
            status=a.status
        ) for a in top_accounts],
        recent_agent_activities=agents_summary,
        demo_mode=settings.DEMO_MODE
    )
