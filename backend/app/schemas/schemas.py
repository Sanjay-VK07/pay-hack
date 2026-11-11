from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator

# Base & Shared
class IndicatorSchema(BaseModel):
    id: str
    indicator_type: str
    indicator_value: str
    risk_weight: float
    details: Dict[str, Any] = {}

class DeviceSchema(BaseModel):
    id: str
    device_fingerprint: str
    device_type: str
    os: str
    browser: str
    is_emulator: bool
    risk_level: str

class PaymentIdentitySchema(BaseModel):
    id: str
    identity_type: str
    identity_hash: str
    masked_value: str
    risk_flags: List[str] = []

class CustomerAccountSchema(BaseModel):
    id: str
    account_number: str
    full_name: str
    email: str
    phone: Optional[str] = None
    country: str
    risk_rating: str
    account_age_days: int
    status: str

# Transactions
class TransactionSchema(BaseModel):
    id: str
    customer_id: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    amount: float
    currency: str
    timestamp: datetime
    payment_status: str
    risk_score: float
    risk_category: str
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    payment_identity_id: Optional[str] = None
    investigation_status: str
    failure_reason: Optional[str] = None
    merchant_name: str

    class Config:
        from_attributes = True

class TransactionIngestSchema(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64)
    amount: float = Field(gt=0, allow_inf_nan=False)
    currency: str = Field(default="USD", min_length=3, max_length=3, pattern="^[A-Za-z]{3}$")
    device_fingerprint: Optional[str] = Field(default=None, max_length=128)
    device_type: Optional[str] = Field(default="DESKTOP", max_length=64)
    os: Optional[str] = Field(default="MacOS", max_length=64)
    browser: Optional[str] = Field(default="Chrome", max_length=64)
    is_emulator: bool = False
    ip_address: Optional[str] = Field(default=None, max_length=64)
    payment_identity_type: Optional[str] = Field(default="CARD_HASH", max_length=64)
    payment_identity_value: Optional[str] = Field(default=None, max_length=128)
    merchant_name: str = Field(default="Global Marketplace", min_length=1, max_length=256)
    payment_status: str = Field(default="COMPLETED", min_length=1, max_length=32)

class TransactionDetailSchema(TransactionSchema):
    customer: Optional[CustomerAccountSchema] = None
    device: Optional[DeviceSchema] = None
    payment_identity: Optional[PaymentIdentitySchema] = None
    indicators: List[IndicatorSchema] = []
    investigations: List[Any] = []

# Graph Schemas
class ConnectedEntitySchema(BaseModel):
    node_id: str
    key: str
    label: str
    type: str
    relationship: str
    risk_level: str
    evidence_id: Optional[str] = None
    suspicious_reason: Optional[str] = None

class SuspiciousConnectionSchema(BaseModel):
    connected_to: str
    relationship: str
    reason: str
    evidence_id: Optional[str] = None

class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # ACCOUNT, TRANSACTION, DEVICE, PAYMENT_IDENTITY, IP_INDICATOR
    risk_score: Optional[float] = None
    risk_level: str = "LOW"
    cluster_id: Optional[str] = None
    position: Dict[str, float] = {}
    connected_entities: List[ConnectedEntitySchema] = []
    suspicious_connections: List[SuspiciousConnectionSchema] = []
    attributes: Dict[str, Any] = {}

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str  # ACCOUNT_USES_DEVICE, ACCOUNT_MADE_TRANSACTION, ACCOUNT_SHARES_PAYMENT_IDENTITY, ACCOUNT_SHARES_IP_INDICATOR, TRANSACTION_LINKED_TO_ACCOUNT
    evidence_id: Optional[str] = None
    is_suspicious: bool = False
    suspicious_reason: Optional[str] = None
    supporting_evidence: Optional[str] = None
    alternative_explanation: Optional[str] = None
    timestamp: Optional[str] = None
    shared_indicator: Optional[str] = None
    attributes: Dict[str, Any] = {}

class GraphDataResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    clusters: List[Dict[str, Any]]
    total_nodes: int
    total_edges: int
    summary: Dict[str, Any] = {}

# Investigation & Case Schemas
class EvidenceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: Optional[str] = None
    evidence_type: str
    source_entity: Optional[str] = None
    target_entity: Optional[str] = None
    observed_value: Optional[str] = None
    baseline_value: Optional[str] = None
    severity: str = "MEDIUM"
    confidence_score: Optional[float] = None
    source_reliability: Optional[str] = None
    corroboration_count: Optional[int] = None
    alternative_explanation: Optional[str] = None
    verification_status: Optional[str] = None
    explanation: Optional[str] = None
    related_transaction_id: Optional[str] = None
    related_account_id: Optional[str] = None
    description: Optional[str] = None
    raw_data: Dict[str, Any] = {}
    timestamp: Optional[datetime] = None
    created_at: datetime

class AgentFindingSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    finding_key: str
    finding_value: str

class AgentExecutionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    agent_name: str
    stage: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_time_ms: int = 0
    input_summary: Optional[str] = None
    findings: Optional[str] = None
    evidence_ids: List[str] = []
    output_json: Dict[str, Any] = {}
    error_message: Optional[str] = None

class RiskAssessmentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    risk_score: float
    risk_level: str
    risk_factors: List[str]
    evidence_ids: List[str]
    scoring_details: Dict[str, Any] = {}
    recommended_action: str
    explanation: str
    isolation_forest_score: Optional[float] = None
    created_at: datetime

class TimelineStageSchema(BaseModel):
    stage_number: int
    stage_name: str
    status: str  # COMPLETED, IN_PROGRESS, PENDING, FAILED, SKIPPED
    timestamp: Optional[str] = None
    actor: str
    summary: str
    evidence_refs: List[str] = []
    raw_data: Dict[str, Any] = {}

class ApprovalRequestSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    action_type: str
    status: str
    requested_by: str
    approved_by: Optional[str] = None
    operation_reference: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

# Payment Schemas
class PaymentOperationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: Optional[str] = None
    paypal_order_id: Optional[str] = None
    capture_id: Optional[str] = None
    transaction_ref: str
    amount: float
    currency: str
    payment_status: str
    refund_status: str
    approval_status: str
    operation_type: str
    idempotency_key: str
    is_simulated: bool
    created_at: datetime
    updated_at: datetime

class CaseDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    primary_transaction_id: str
    fraud_cluster_id: Optional[str] = None
    related_accounts: List[str] = []
    risk_level: str
    status: str
    evidence_count: int
    assigned_investigator: str
    recommended_action: str
    approval_status: str
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    primary_transaction: Optional[TransactionSchema] = None
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    customer_email: Optional[str] = None
    customer_risk_rating: Optional[str] = None
    transaction_amount: Optional[float] = None
    currency: str = "USD"
    payment_status: Optional[str] = None
    paypal_eligible: bool = False
    capture_id: Optional[str] = None
    financial_impact: float = 0.0
    operation_reference: Optional[str] = None
    approving_user: Optional[str] = None
    approval_timestamp: Optional[datetime] = None
    evidence: List[EvidenceSchema] = []
    agent_executions: List[AgentExecutionSchema] = []
    risk_assessments: List[RiskAssessmentSchema] = []
    approval_requests: List[ApprovalRequestSchema] = []
    payment_operations: List[PaymentOperationSchema] = []
    reasoning_timeline: List[TimelineStageSchema] = []
    scoring_details: Dict[str, Any] = {}
    paypal_verification: Dict[str, Any] = {}
    approval_integrity_valid: bool = True
    approval_integrity_warning: Optional[str] = None

class CaseApprovalAction(BaseModel):
    action: str  # APPROVE or REJECT
    investigator_name: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("investigator_name", "reason")
    @classmethod
    def require_non_whitespace(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A non-empty value is required")
        return value

class CreateOrderSchema(BaseModel):
    amount: float = Field(gt=0, allow_inf_nan=False)
    currency: str = Field(default="USD", min_length=3, max_length=3, pattern="^[A-Za-z]{3}$")
    transaction_ref: Optional[str] = Field(default=None, max_length=64)
    case_id: Optional[str] = Field(default=None, max_length=64)
    description: str = Field(default="AgentShield Protected FinTech Checkout", min_length=1, max_length=127)

class RefundRequestSchema(BaseModel):
    payment_id: Optional[str] = Field(default=None, max_length=64)
    amount: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3, pattern="^[A-Za-z]{3}$")
    reason: str = Field(min_length=1, max_length=1000)
    investigator: str = Field(min_length=1, max_length=128)

    @field_validator("reason", "investigator")
    @classmethod
    def require_non_whitespace(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A non-empty value is required")
        return value

# Audit Schemas
class AuditLogSchema(BaseModel):
    id: str
    case_id: Optional[str] = None
    transaction_id: Optional[str] = None
    event_type: str
    actor: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    api_ref: Optional[str] = None
    details: Dict[str, Any] = {}
    created_at: datetime

# Dashboard Schemas
class DashboardSummarySchema(BaseModel):
    total_transactions_analyzed: int
    suspicious_transactions: int
    legitimate_transactions: int = 0
    active_investigation_cases: int
    resolved_cases: int
    total_cases_count: int = 0
    total_agent_executions_count: int = 0
    high_risk_accounts: int
    fraud_networks_discovered: int
    estimated_financial_exposure: float
    paypal_operations_count: int
    risk_distribution: Dict[str, int]
    daily_trend: List[Dict[str, Any]]
    recent_transactions: List[TransactionSchema]
    recent_cases: List[Dict[str, Any]]
    top_risk_accounts: List[CustomerAccountSchema]
    recent_agent_activities: List[Dict[str, Any]]
    demo_mode: bool
