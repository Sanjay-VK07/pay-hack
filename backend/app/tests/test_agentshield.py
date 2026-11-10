import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.models import CustomerAccount, Device, PaymentIdentity, Transaction, PaymentOperation, InvestigationCase
from app.services.seed_service import SeedService
from app.graph.graph_service import GraphIntelligenceEngine
from app.fraud.risk_engine import DeterministicRiskEngine
from app.agents.orchestrator import MultiAgentOrchestrator
from app.paypal.simulator import PayPalSimulator

# In-memory SQLite for testing
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    seeder = SeedService(session)
    seeder.seed_demo_dataset()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_database_seeding(db):
    accounts_count = db.query(CustomerAccount).count()
    txns_count = db.query(Transaction).count()
    assert accounts_count == 12
    assert txns_count >= 25

def test_graph_construction_and_cluster_detection(db):
    engine = GraphIntelligenceEngine(db)
    engine.build_graph()
    assert engine.G.number_of_nodes() > 20
    assert engine.G.number_of_edges() > 20

    clusters = engine.detect_fraud_clusters()
    assert len(clusters) > 0
    
    # Check that coordinated syndicate is flagged as coordinated
    coordinated_clusters = [c for c in clusters if c.get("is_coordinated")]
    assert len(coordinated_clusters) >= 1
    top_cluster = coordinated_clusters[0]
    assert top_cluster["risk_score"] >= 80.0
    assert top_cluster["member_accounts_count"] >= 3

def test_deterministic_risk_scoring(db):
    engine = DeterministicRiskEngine(db)
    
    # Test legitimate transaction
    legit_txn = db.query(Transaction).filter(Transaction.id == "TXN_101").first()
    res_legit = engine.evaluate_transaction(legit_txn)
    assert res_legit["risk_level"] == "LOW"
    assert res_legit["risk_score"] < 40.0
    assert res_legit["recommended_action"] == "ALLOW"

    # Test fraud syndicate transaction
    fraud_txn = db.query(Transaction).filter(Transaction.id == "TXN_FRAUD_901").first()
    res_fraud = engine.evaluate_transaction(fraud_txn, {"is_coordinated": True, "name": "Syndicate 1", "member_accounts_count": 4, "id": "CLUSTER_001"})
    assert res_fraud["risk_level"] == "CRITICAL"
    assert res_fraud["risk_score"] >= 85.0
    assert res_fraud["recommended_action"] == "REFUND_TRANSACTION"
    assert len(res_fraud["risk_factors"]) >= 3

def test_multi_agent_orchestration(db):
    orchestrator = MultiAgentOrchestrator(db)
    result = orchestrator.run_investigation("TXN_FRAUD_901")
    assert result["case_id"] is not None
    assert result["risk_level"] == "CRITICAL"
    assert len(result["agent_executions"]) == 6

    # Check case persisted
    case = db.query(InvestigationCase).filter(InvestigationCase.id == result["case_id"]).first()
    assert case is not None
    assert case.evidence_count >= 3
    assert case.recommended_action == "REFUND_TRANSACTION"

def test_paypal_simulator_and_idempotency(db):
    sim = PayPalSimulator()
    order = sim.create_simulated_order(2450.00)
    assert order["is_simulated"] is True
    assert order["status"] == "CREATED"

    capture = sim.capture_simulated_order(order["id"], 2450.00)
    assert capture["is_simulated"] is True
    cap_id = capture["purchase_units"][0]["payments"]["captures"][0]["id"]

    refund = sim.refund_simulated_capture(cap_id, 2450.00)
    assert refund["is_simulated"] is True
    assert refund["status"] == "COMPLETED"
    assert refund["amount"]["value"] == "2450.00"
