import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Index
)
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(64), primary_key=True)
    username = Column(String(128), unique=True, nullable=False, index=True)
    email = Column(String(256), unique=True, nullable=False)
    role = Column(String(64), default="INVESTIGATOR")  # ADMIN, INVESTIGATOR, ANALYST
    created_at = Column(DateTime(timezone=True), default=utcnow)

class CustomerAccount(Base):
    __tablename__ = "customer_accounts"
    
    id = Column(String(64), primary_key=True)
    account_number = Column(String(64), unique=True, nullable=False, index=True)
    full_name = Column(String(256), nullable=False)
    email = Column(String(256), nullable=False, index=True)
    phone = Column(String(64), nullable=True)
    country = Column(String(64), default="US")
    risk_rating = Column(String(32), default="LOW")  # LOW, MEDIUM, HIGH, CRITICAL
    account_age_days = Column(Integer, default=30)
    status = Column(String(32), default="ACTIVE")  # ACTIVE, SUSPENDED, UNDER_REVIEW
    created_at = Column(DateTime(timezone=True), default=utcnow)
    
    transactions = relationship("Transaction", back_populates="customer")

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(String(64), primary_key=True)
    device_fingerprint = Column(String(128), unique=True, nullable=False, index=True)
    device_type = Column(String(64), default="DESKTOP")  # MOBILE, DESKTOP, EMULATOR, BOT
    os = Column(String(64), default="Windows")
    browser = Column(String(64), default="Chrome")
    is_emulator = Column(Boolean, default=False)
    risk_level = Column(String(32), default="LOW")
    first_seen = Column(DateTime(timezone=True), default=utcnow)
    last_seen = Column(DateTime(timezone=True), default=utcnow)

class PaymentIdentity(Base):
    __tablename__ = "payment_identities"
    
    id = Column(String(64), primary_key=True)
    identity_type = Column(String(64), nullable=False)  # CARD_HASH, PAYPAL_EMAIL, BANK_TOKEN
    identity_hash = Column(String(128), unique=True, nullable=False, index=True)
    masked_value = Column(String(128), nullable=False)  # e.g. "•••• 4242" or "f***@evil.com"
    risk_flags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=utcnow)

class FraudCluster(Base):
    __tablename__ = "fraud_clusters"
    
    id = Column(String(64), primary_key=True)
    name = Column(String(256), nullable=False)
    risk_score = Column(Float, default=0.0)
    cluster_type = Column(String(64), default="COORDINATED_RING")  # COORDINATED_RING, DEVICE_SPOOFING, VELOCITY_ATTACK
    member_accounts_count = Column(Integer, default=0)
    member_transactions_count = Column(Integer, default=0)
    summary = Column(Text, nullable=True)
    indicators = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    
    investigations = relationship("InvestigationCase", back_populates="fraud_cluster")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String(64), primary_key=True)
    customer_id = Column(String(64), ForeignKey("customer_accounts.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    timestamp = Column(DateTime(timezone=True), default=utcnow, index=True)
    payment_status = Column(String(32), default="COMPLETED")  # COMPLETED, FAILED, PENDING, REFUNDED
    risk_score = Column(Float, default=0.0)  # 0.0 to 100.0
    risk_category = Column(String(32), default="LOW")  # LOW, MEDIUM, HIGH, CRITICAL
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=True, index=True)
    ip_address = Column(String(64), nullable=True, index=True)
    payment_identity_id = Column(String(64), ForeignKey("payment_identities.id"), nullable=True)
    investigation_status = Column(String(32), default="NONE")  # NONE, PENDING, INVESTIGATING, ESCALATED, RESOLVED
    failure_reason = Column(String(256), nullable=True)
    merchant_name = Column(String(128), default="Global Marketplace")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    
    customer = relationship("CustomerAccount", back_populates="transactions")
    device = relationship("Device")
    payment_identity = relationship("PaymentIdentity")
    indicators = relationship("TransactionIndicator", back_populates="transaction")
    investigations = relationship("InvestigationCase", back_populates="primary_transaction")

class TransactionIndicator(Base):
    __tablename__ = "transaction_indicators"
    
    id = Column(String(64), primary_key=True)
    transaction_id = Column(String(64), ForeignKey("transactions.id"), nullable=False, index=True)
    indicator_type = Column(String(64), nullable=False)  # IP, DEVICE, VELOCITY, CARD_HASH, GEO_MISMATCH
    indicator_value = Column(String(256), nullable=False)
    risk_weight = Column(Float, default=1.0)
    details = Column(JSON, default=dict)
    
    transaction = relationship("Transaction", back_populates="indicators")

class InvestigationCase(Base):
    __tablename__ = "investigation_cases"
    
    id = Column(String(64), primary_key=True)
    primary_transaction_id = Column(String(64), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    fraud_cluster_id = Column(String(64), ForeignKey("fraud_clusters.id", ondelete="SET NULL"), nullable=True, index=True)
    related_accounts = Column(JSON, default=list)  # List of account IDs
    risk_level = Column(String(32), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(32), default="PENDING_REVIEW")  # DETECTED, INVESTIGATING, PENDING_REVIEW, APPROVED, REJECTED, ACTION_QUEUED, ACTION_EXECUTING, ACTION_COMPLETED, ACTION_FAILED, CLOSED
    evidence_count = Column(Integer, default=0)
    assigned_investigator = Column(String(128), default="Autonomous Security Agent")
    recommended_action = Column(String(64), default="REVIEW")  # ALLOW, REVIEW, RESTRICT_ACCOUNT, REFUND_TRANSACTION, BLOCK_NETWORK
    approval_status = Column(String(32), default="PENDING")  # PENDING, APPROVED, REJECTED
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    
    primary_transaction = relationship("Transaction", back_populates="investigations")
    fraud_cluster = relationship("FraudCluster", back_populates="investigations")
    evidence = relationship("InvestigationEvidence", back_populates="case", cascade="all, delete-orphan")
    agent_executions = relationship("AgentExecution", back_populates="case", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="case", cascade="all, delete-orphan")
    approval_requests = relationship("ApprovalRequest", back_populates="case", cascade="all, delete-orphan")
    payment_operations = relationship("PaymentOperation", back_populates="case")

class InvestigationEvidence(Base):
    __tablename__ = "investigation_evidence"
    
    id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("investigation_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_type = Column(String(64), nullable=False)  # VELOCITY_SPIKE, DEVICE_FINGERPRINT, SHARED_PAYMENT_IDENTITY, FAILED_AUTH_SPIKE, AMOUNT_THRESHOLD, COORDINATED_FRAUD_CLUSTER, GEO_PROXY_IP
    source_entity = Column(String(64), nullable=True)  # e.g. "TXN_FRAUD_901" or "ACC_009"
    target_entity = Column(String(64), nullable=True)  # e.g. "DEV_007" or "PID_006" or IP
    observed_value = Column(String(256), nullable=True)  # Actual observed value e.g. "4 transactions in 60 minutes"
    baseline_value = Column(String(256), nullable=True)  # Expected or baseline value e.g. "Max 1 transaction per 24 hours"
    severity = Column(String(32), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    confidence_score = Column(Float, default=0.95)  # 0.0 - 1.0 confidence
    source_reliability = Column(String(64), default="HIGH - Verified Hardware / Network Telemetry")
    corroboration_count = Column(Integer, default=1)  # Number of corroborating signals
    alternative_explanation = Column(Text, nullable=True)  # Plausible legitimate explanation
    verification_status = Column(String(32), default="VERIFIED")  # VERIFIED, UNVERIFIED, CORROBORATED
    explanation = Column(Text, nullable=True)  # Explanation of relevance to fraud
    related_transaction_id = Column(String(64), nullable=True, index=True)
    related_account_id = Column(String(64), nullable=True, index=True)
    description = Column(Text, nullable=True)  # Summary description for backward compatibility
    raw_data = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), default=utcnow)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    
    case = relationship("InvestigationCase", back_populates="evidence")

class AgentExecution(Base):
    __tablename__ = "agent_executions"
    
    id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("investigation_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name = Column(String(128), nullable=False)
    stage = Column(String(64), nullable=False)  # TRANSACTION_INTEL, IDENTITY_INTEL, GRAPH_ENGINE, FRAUD_INVESTIGATION, RISK_ASSESSMENT, RESPONSE
    status = Column(String(32), default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED
    started_at = Column(DateTime(timezone=True), default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    execution_time_ms = Column(Integer, default=0)
    input_summary = Column(Text, nullable=True)
    findings = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0)
    evidence_ids = Column(JSON, default=list)  # Evidence IDs backing the agent's findings
    output_json = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    
    case = relationship("InvestigationCase", back_populates="agent_executions")
    findings_records = relationship("AgentFinding", back_populates="execution", cascade="all, delete-orphan")

class AgentFinding(Base):
    __tablename__ = "agent_findings"
    
    id = Column(String(64), primary_key=True)
    execution_id = Column(String(64), ForeignKey("agent_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_key = Column(String(128), nullable=False)
    finding_value = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    
    execution = relationship("AgentExecution", back_populates="findings_records")

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    
    id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("investigation_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(String(64), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String(32), default="LOW")
    risk_factors = Column(JSON, default=list)
    evidence_ids = Column(JSON, default=list)
    scoring_details = Column(JSON, default=dict)  # Mathematical formula, factor weights, raw vs normalized
    recommended_action = Column(String(64), default="ALLOW")
    explanation = Column(Text, nullable=False)
    isolation_forest_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    
    case = relationship("InvestigationCase", back_populates="risk_assessments")

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    
    id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("investigation_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(64), nullable=False)  # REFUND_PAYMENT, RESTRICT_ACCOUNT, BLOCK_PAYMENT_IDENTITY
    status = Column(String(32), default="PENDING")  # PENDING, APPROVED, REJECTED
    requested_by = Column(String(128), default="Autonomous Risk Agent")
    approved_by = Column(String(128), nullable=True)
    operation_reference = Column(String(128), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    case = relationship("InvestigationCase", back_populates="approval_requests")

class PaymentOperation(Base):
    __tablename__ = "payment_operations"
    
    id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("investigation_cases.id", ondelete="SET NULL"), nullable=True, index=True)
    paypal_order_id = Column(String(128), nullable=True, index=True)
    capture_id = Column(String(128), nullable=True, index=True)
    transaction_ref = Column(String(64), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    payment_status = Column(String(32), default="COMPLETED")  # COMPLETED, CAPTURED, REFUNDED, FAILED
    refund_status = Column(String(32), default="NONE")  # NONE, PENDING, COMPLETED, FAILED
    approval_status = Column(String(32), default="PENDING")  # PENDING, APPROVED, REJECTED
    operation_type = Column(String(64), default="REFUND")  # REFUND, HOLD, DISPUTE
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)
    raw_response = Column(JSON, default=dict)
    is_simulated = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    
    case = relationship("InvestigationCase", back_populates="payment_operations")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(64), primary_key=True)
    case_id = Column(String(64), nullable=True, index=True)
    transaction_id = Column(String(64), nullable=True, index=True)
    event_type = Column(String(64), nullable=False)  # INGESTION, ANALYSIS, CLUSTER_DETECTED, CASE_CREATED, APPROVAL, REFUND_EXECUTED
    actor = Column(String(128), nullable=False)  # User or Agent Name
    previous_state = Column(String(64), nullable=True)
    new_state = Column(String(64), nullable=True)
    api_ref = Column(String(128), nullable=True)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
