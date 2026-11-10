from fastapi import APIRouter
from app.api.dashboard import router as dashboard_router
from app.api.transactions import router as transactions_router
from app.api.fraud_networks import router as fraud_networks_router
from app.api.investigations import router as investigations_router
from app.api.agents import router as agents_router
from app.api.payments import router as payments_router
from app.api.audit import router as audit_router
from app.api.demo import router as demo_router

api_router = APIRouter(prefix="/api")

api_router.include_router(dashboard_router)
api_router.include_router(transactions_router)
api_router.include_router(fraud_networks_router)
api_router.include_router(investigations_router)
api_router.include_router(agents_router)
api_router.include_router(payments_router)
api_router.include_router(audit_router)
api_router.include_router(demo_router)

@api_router.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "HEALTHY",
        "service": "AgentShield Autonomous FinTech Engine",
        "version": "1.0.0"
    }
