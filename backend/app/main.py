from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.api.router import api_router
from app.models.models import Transaction
from app.services.seed_service import SeedService

import logging

logger = logging.getLogger("agentshield")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Security check: warn if exposed on public/wildcard interface without configured API key
    if settings.API_HOST in ("0.0.0.0", "::") and not settings.AGENTSHIELD_API_KEY:
        logger.warning(
            "SECURITY WARNING: Backend is configured on wildcard interface '%s' without AGENTSHIELD_API_KEY. "
            "All mutating operations from non-loopback callers will be rejected with HTTP 403 Forbidden. "
            "For secure remote access, set AGENTSHIELD_API_KEY in backend/.env.",
            settings.API_HOST,
        )

    # Startup: Create tables if not present
    Base.metadata.create_all(bind=engine)
    
    # Check if database needs initial seeding
    db = SessionLocal()
    try:
        tx_count = db.query(Transaction).count()
        if tx_count == 0:
            seeder = SeedService(db)
            seeder.seed_demo_dataset()
    finally:
        db.close()
    
    yield
    # Shutdown

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Autonomous Multi-Agent Payment Fraud Investigation and Prevention Platform.\n\n"
        "### Security Architecture & Operational Scope\n"
        "- **Mutation Authentication Guard:** All 14 mutating endpoints (`POST /api/investigations/*`, `POST /api/payments/*`, `POST /api/transactions/*`, `POST /api/demo/*`) "
        "enforce authentication via `X-AgentShield-Key` header or `Authorization: Bearer <token>` matching `AGENTSHIELD_API_KEY`.\n"
        "- **Loopback Protection Mode:** When `AGENTSHIELD_API_KEY` is unset in backend environment, unauthenticated mutating requests from non-loopback network clients "
        "are strictly blocked with HTTP 403 Forbidden. Loopback clients (`127.0.0.1`, `::1`) are permitted for frictionless local demo evaluation.\n"
        "- **Read-Only Demo Access:** All query endpoints (`GET /api/*`) remain unauthenticated to allow seamless dashboard, graph, and transaction inspection.\n"
        "- **Financial & State Safeguards:** State transitions (approval gates, payment capture/refund dispatches) enforce strict server-side state machines, "
        "cross-record relational consistency, idempotency locks, and human approval verification regardless of transport authentication."
    ),
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS configuration for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    # Keep credentialed browser requests limited to the local demo frontend.
    # A wildcard here would allow any website to make credentialed requests.
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type", "Origin", "X-AgentShield-Key"],
)

app.include_router(api_router)

@app.get("/")
def root():
    return {
        "service": "AgentShield FinTech Fraud Intelligence",
        "tagline": "Intelligence Behind Every Transaction",
        "status": "OPERATIONAL",
        "docs_url": "/docs",
        "api_prefix": "/api"
    }

if __name__ == "__main__":
    import uvicorn
    # Local demo by default. Network exposure requires an explicit operator choice.
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=8000,
        reload=True,
    )
