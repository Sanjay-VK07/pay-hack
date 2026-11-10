from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.api.router import api_router
from app.models.models import Transaction
from app.services.seed_service import SeedService

@asynccontextmanager
async def lifespan(app: FastAPI):
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
    description="Autonomous Multi-Agent Payment Fraud Investigation and Prevention Platform",
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
    allow_headers=["Accept", "Authorization", "Content-Type", "Origin"],
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
