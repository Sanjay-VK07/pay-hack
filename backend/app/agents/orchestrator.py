import uuid
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.models import (
    Transaction, CustomerAccount, Device, PaymentIdentity,
    InvestigationCase, InvestigationEvidence, AgentExecution,
    AgentFinding, RiskAssessment, ApprovalRequest, AuditLog, FraudCluster
)
from app.graph.graph_service import GraphIntelligenceEngine
from app.fraud.risk_engine import DeterministicRiskEngine
from app.fraud.anomaly_detector import AnomalyDetector
from app.agents.transaction_agent import TransactionIntelligenceAgent
from app.agents.identity_agent import IdentityIntelligenceAgent
from app.agents.graph_agent import GraphIntelligenceAgent
from app.agents.investigation_agent import FraudInvestigationAgent
from app.agents.risk_agent import RiskAssessmentAgent
from app.agents.response_agent import ResponseAgent

def utcnow():
    return datetime.now(timezone.utc)

class MultiAgentOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.tx_agent = TransactionIntelligenceAgent()
        self.id_agent = IdentityIntelligenceAgent()
        self.graph_engine = GraphIntelligenceEngine(db)
        self.graph_agent = GraphIntelligenceAgent()
        self.inv_agent = FraudInvestigationAgent()
        self.risk_engine = DeterministicRiskEngine(db)
        self.anomaly_detector = AnomalyDetector(db)
        self.risk_agent = RiskAssessmentAgent()
        self.resp_agent = ResponseAgent()

    def run_investigation(
        self,
        transaction_id: str,
        actor: str = "Autonomous Security Agent",
        force_new_case: bool = False
    ) -> Dict[str, Any]:
        """
        Executes end-to-end multi-agent investigation workflow:
        Transaction -> Identity -> Graph -> Investigation -> Risk -> Human Gate -> Response -> Audit
        """
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")

        # 1. Existing Case Check (Avoid unnecessary duplicate cases)
        existing_case = None
        if not force_new_case:
            existing_case = self.db.query(InvestigationCase).filter(
                InvestigationCase.primary_transaction_id == transaction_id
            ).first()

        case_id = existing_case.id if existing_case else f"CASE_{transaction_id.replace('TXN_', '')}"
        
        # 2. Gather context
        customer = transaction.customer
        device = transaction.device
        payment_identity = transaction.payment_identity

        prior_failed_count = self.db.query(Transaction).filter(
            Transaction.customer_id == transaction.customer_id,
            Transaction.payment_status == "FAILED"
        ).count()

        recent_count = self.db.query(Transaction).filter(
            Transaction.customer_id == transaction.customer_id,
            Transaction.id != transaction.id
        ).count()

        shared_dev_accounts = 0
        if device:
            shared_dev_accounts = self.db.query(Transaction.customer_id).filter(
                Transaction.device_id == device.id
            ).distinct().count()

        shared_pid_accounts = 0
        if payment_identity:
            shared_pid_accounts = self.db.query(Transaction.customer_id).filter(
                Transaction.payment_identity_id == payment_identity.id
            ).distinct().count()

        # Step 1: Transaction Intelligence Agent
        tx_result = self.tx_agent.execute({
            "transaction": {"id": transaction.id, "amount": transaction.amount, "currency": transaction.currency},
            "customer": {"id": customer.id, "full_name": customer.full_name, "email": customer.email} if customer else {},
            "prior_failed_count": prior_failed_count,
            "recent_count": recent_count
        })

        # Step 2: Identity Intelligence Agent
        id_result = self.id_agent.execute({
            "device": {
                "id": device.id if device else None,
                "device_fingerprint": device.device_fingerprint if device else "",
                "device_type": device.device_type if device else "",
                "is_emulator": device.is_emulator if device else False
            } if device else {},
            "payment_identity": {
                "id": payment_identity.id if payment_identity else None,
                "masked_value": payment_identity.masked_value if payment_identity else "",
                "risk_flags": payment_identity.risk_flags if payment_identity else []
            } if payment_identity else {},
            "customer": {"account_age_days": customer.account_age_days if customer else 30},
            "shared_accounts_count": shared_dev_accounts,
            "shared_identities_count": shared_pid_accounts,
            "ip_address": transaction.ip_address
        })

        # Step 3: Graph Intelligence Engine & Graph Agent
        self.graph_engine.build_graph()
        clusters = self.graph_engine.detect_fraud_clusters()
        
        # Match transaction or customer to cluster
        matched_cluster = None
        for c in clusters:
            if transaction.id in c["transaction_ids"] or (customer and customer.id in c["account_ids"]):
                matched_cluster = c
                break

        # Compute two-hop neighborhood from NetworkX graph
        two_hop_nodes = set()
        if self.graph_engine.G.has_node(transaction.id):
            one_hop = set(self.graph_engine.G.neighbors(transaction.id))
            for nbr in one_hop:
                two_hop_nodes.update(self.graph_engine.G.neighbors(nbr))
            two_hop_nodes |= one_hop
        elif customer and self.graph_engine.G.has_node(customer.id):
            one_hop = set(self.graph_engine.G.neighbors(customer.id))
            for nbr in one_hop:
                two_hop_nodes.update(self.graph_engine.G.neighbors(nbr))
            two_hop_nodes |= one_hop

        graph_result = self.graph_agent.execute({
            "cluster_info": matched_cluster or {},
            "related_accounts": matched_cluster.get("account_ids", []) if matched_cluster else ([customer.id] if customer else []),
            "shared_devices": [device.id] if (device and shared_dev_accounts > 1) else [],
            "shared_identities": [payment_identity.id] if (payment_identity and shared_pid_accounts > 1) else [],
            "two_hop_count": len(two_hop_nodes),
            "total_cluster_exposure": matched_cluster.get("total_transaction_value", transaction.amount) if matched_cluster else transaction.amount
        })

        # Step 4: Fraud Investigation Agent
        inv_result = self.inv_agent.execute({
            "cluster_info": matched_cluster or {},
            "graph_findings": graph_result.get("findings"),
            "transaction_findings": tx_result.get("findings"),
            "identity_findings": id_result.get("findings"),
            "related_accounts": matched_cluster.get("account_ids", []) if matched_cluster else []
        })

        # Step 5: Deterministic Risk Engine & Anomaly Detector
        deterministic_risk = self.risk_engine.evaluate_transaction(transaction, matched_cluster)
        anomaly_score = self.anomaly_detector.score_transaction(transaction)

        # Update transaction's verified risk score
        transaction.risk_score = deterministic_risk["risk_score"]
        transaction.risk_category = deterministic_risk["risk_level"]
        transaction.investigation_status = "INVESTIGATING" if deterministic_risk["risk_level"] in ("HIGH", "CRITICAL") else "RESOLVED"

        # Step 6: Risk Assessment Agent
        risk_result = self.risk_agent.execute({
            "deterministic_risk": deterministic_risk,
            "anomaly_score": anomaly_score,
            "investigation_findings": inv_result.get("findings")
        })

        # Step 7: Response Agent
        approval_status = existing_case.approval_status if existing_case else "PENDING"
        resp_result = self.resp_agent.execute({
            "risk_findings": risk_result.get("findings"),
            "transaction": {"id": transaction.id, "amount": transaction.amount, "currency": transaction.currency},
            "approval_status": approval_status
        })

        # 3. Persist Investigation Case and Records
        raw_evidence_records = deterministic_risk.get("evidence_records", [])
        actual_evidence_count = len(raw_evidence_records)

        # Ensure FraudCluster record exists if matched
        cluster_id = None
        if matched_cluster and matched_cluster.get("id"):
            cluster_id = matched_cluster["id"]
            existing_fc = self.db.query(FraudCluster).filter(FraudCluster.id == cluster_id).first()
            if not existing_fc:
                new_fc = FraudCluster(
                    id=cluster_id,
                    name=matched_cluster.get("name", f"Discovered Cluster {cluster_id}"),
                    risk_score=matched_cluster.get("risk_score", 90.0),
                    cluster_type=matched_cluster.get("cluster_type", "COORDINATED_RING"),
                    member_accounts_count=matched_cluster.get("member_accounts_count", len(matched_cluster.get("account_ids", []))),
                    member_transactions_count=matched_cluster.get("member_transactions_count", len(matched_cluster.get("transaction_ids", []))),
                    summary=matched_cluster.get("summary", "Identified coordinated fraud ring through graph community detection."),
                    indicators=matched_cluster.get("indicators", [])
                )
                self.db.add(new_fc)
                self.db.flush()

        if not existing_case:
            case = InvestigationCase(
                id=case_id,
                primary_transaction_id=transaction.id,
                fraud_cluster_id=cluster_id,
                related_accounts=matched_cluster.get("account_ids", [customer.id if customer else ""]) if matched_cluster else [customer.id if customer else ""],
                risk_level=deterministic_risk["risk_level"],
                status="PENDING_REVIEW" if deterministic_risk["risk_level"] in ("HIGH", "CRITICAL") else "CLOSED",
                evidence_count=actual_evidence_count,
                assigned_investigator="AgentShield Autonomous Investigator",
                recommended_action=deterministic_risk["recommended_action"],
                approval_status="PENDING",
                summary=risk_result.get("summary")
            )
            self.db.add(case)
            self.db.flush()
        else:
            case = existing_case
            case.risk_level = deterministic_risk["risk_level"]
            case.evidence_count = actual_evidence_count
            case.recommended_action = deterministic_risk["recommended_action"]
            case.summary = risk_result.get("summary")
            # Preserve existing approval/completed status if already decided
            if case.status not in ("APPROVED", "REJECTED", "ACTION_QUEUED", "ACTION_EXECUTING", "ACTION_COMPLETED", "CLOSED"):
                case.status = "PENDING_REVIEW" if deterministic_risk["risk_level"] in ("HIGH", "CRITICAL") else "CLOSED"
            case.updated_at = utcnow()

        # Save Structured Evidence Records (Replace previous for this case to maintain exact 1:1 count)
        self.db.query(InvestigationEvidence).filter(InvestigationEvidence.case_id == case.id).delete()
        for idx, ev_data in enumerate(raw_evidence_records):
            ev_unique_id = f"EV_{case.id}_{idx+1:02d}_{ev_data.get('evidence_type', 'IND')[:10]}"
            ev_record = InvestigationEvidence(
                id=ev_unique_id,
                case_id=case.id,
                evidence_type=ev_data.get("evidence_type", "CORRELATED_INDICATOR"),
                source_entity=ev_data.get("source_entity"),
                target_entity=ev_data.get("target_entity"),
                observed_value=ev_data.get("observed_value"),
                baseline_value=ev_data.get("baseline_value"),
                severity=ev_data.get("severity", deterministic_risk["risk_level"]),
                confidence_score=ev_data.get("confidence_score", 0.95),
                source_reliability=ev_data.get("source_reliability", "HIGH - Verified Hardware / Network Telemetry"),
                corroboration_count=ev_data.get("corroboration_count", 1),
                alternative_explanation=ev_data.get("alternative_explanation"),
                verification_status=ev_data.get("verification_status", "VERIFIED"),
                explanation=ev_data.get("explanation"),
                related_transaction_id=ev_data.get("related_transaction_id", transaction.id),
                related_account_id=ev_data.get("related_account_id", customer.id if customer else None),
                description=ev_data.get("description", ev_data.get("explanation")),
                raw_data={"transaction_id": transaction.id, "cluster": matched_cluster.get("id") if matched_cluster else None},
                timestamp=transaction.timestamp or utcnow()
            )
            self.db.add(ev_record)

        # Categorize evidence IDs per agent stage
        stage_evidence_map = {
            "TRANSACTION_INTEL": [ev.get("id") for ev in raw_evidence_records if "VELOCITY" in ev.get("evidence_type", "") or "AMOUNT" in ev.get("evidence_type", "") or "FAIL" in ev.get("evidence_type", "")],
            "IDENTITY_INTEL": [ev.get("id") for ev in raw_evidence_records if "DEVICE" in ev.get("evidence_type", "") or "PAYMENT" in ev.get("evidence_type", "") or "PROXY" in ev.get("evidence_type", "") or "NEW_ACCT" in ev.get("evidence_type", "")],
            "GRAPH_INTEL": [ev.get("id") for ev in raw_evidence_records if "CLUSTER" in ev.get("evidence_type", "") or "DEVICE_SHARING" in ev.get("evidence_type", "") or "SHARED_PAYMENT" in ev.get("evidence_type", "")],
            "FRAUD_INVESTIGATION": [ev.get("id") for ev in raw_evidence_records if "CLUSTER" in ev.get("evidence_type", "") or "DEVICE" in ev.get("evidence_type", "") or "PAYMENT" in ev.get("evidence_type", "")],
            "RISK_ASSESSMENT": [ev.get("id") for ev in raw_evidence_records],
            "RESPONSE": [ev.get("id") for ev in raw_evidence_records if ev.get("severity") in ("CRITICAL", "HIGH")]
        }

        # Record Agent Executions across all 6 specialized agents
        agent_runs = [
            ("Transaction Intelligence Agent", "TRANSACTION_INTEL", tx_result, max(12, int(tx_result.get("duration_ms", 42)))),
            ("Identity Intelligence Agent", "IDENTITY_INTEL", id_result, max(15, int(id_result.get("duration_ms", 68)))),
            ("Graph Intelligence Agent", "GRAPH_INTEL", graph_result, max(18, int(graph_result.get("duration_ms", 54)))),
            ("Fraud Investigation Agent", "FRAUD_INVESTIGATION", inv_result, max(20, int(inv_result.get("duration_ms", 95)))),
            ("Risk Assessment Agent", "RISK_ASSESSMENT", risk_result, max(14, int(risk_result.get("duration_ms", 53)))),
            ("Autonomous Response Agent", "RESPONSE", resp_result, max(10, int(resp_result.get("duration_ms", 34))))
        ]

        for ag_name, stage, res, exec_ms in agent_runs:
            exec_id = f"EXEC_{case.id}_{stage}"
            existing_exec = self.db.query(AgentExecution).filter(AgentExecution.id == exec_id).first()
            if existing_exec:
                existing_exec.status = res.get("status", "COMPLETED")
                existing_exec.findings = res.get("summary")
                existing_exec.output_json = res.get("output_json", {})
                existing_exec.confidence_score = res.get("confidence_score", 0.95)
                existing_exec.evidence_ids = stage_evidence_map.get(stage, [])
                existing_exec.execution_time_ms = exec_ms
                existing_exec.completed_at = utcnow()
            else:
                exec_record = AgentExecution(
                    id=exec_id,
                    case_id=case.id,
                    agent_name=ag_name,
                    stage=stage,
                    status=res.get("status", "COMPLETED"),
                    started_at=utcnow(),
                    completed_at=utcnow(),
                    execution_time_ms=exec_ms,
                    input_summary=f"Processed transaction {transaction.id} and associated telemetry",
                    findings=res.get("summary"),
                    confidence_score=res.get("confidence_score", 0.95),
                    evidence_ids=stage_evidence_map.get(stage, []),
                    output_json=res.get("output_json", {})
                )
                self.db.add(exec_record)

            # Persist individual AgentFinding records for structured traceability
            findings_data = res.get("findings", {})
            if isinstance(findings_data, dict):
                for f_key, f_val in findings_data.items():
                    val_str = json.dumps(f_val) if isinstance(f_val, (dict, list)) else str(f_val)
                    finding_record_id = f"FND_{exec_id}_{f_key[:20]}"
                    existing_fnd = self.db.query(AgentFinding).filter(AgentFinding.id == finding_record_id).first()
                    if not existing_fnd:
                        fnd = AgentFinding(
                            id=finding_record_id,
                            execution_id=exec_id,
                            finding_key=f_key,
                            finding_value=val_str,
                            confidence=res.get("confidence_score", 0.95),
                            created_at=utcnow()
                        )
                        self.db.add(fnd)

        # Save Risk Assessment Record
        risk_assess_id = f"RA_{case.id}"
        ra = self.db.query(RiskAssessment).filter(RiskAssessment.id == risk_assess_id).first()
        if not ra:
            ra = RiskAssessment(
                id=risk_assess_id,
                case_id=case.id,
                transaction_id=transaction.id,
                risk_score=deterministic_risk["risk_score"],
                risk_level=deterministic_risk["risk_level"],
                risk_factors=deterministic_risk["risk_factors"],
                evidence_ids=deterministic_risk["evidence_ids"],
                scoring_details=deterministic_risk.get("scoring_details", {}),
                recommended_action=deterministic_risk["recommended_action"],
                explanation=deterministic_risk["explanation"],
                isolation_forest_score=anomaly_score
            )
            self.db.add(ra)
        else:
            ra.risk_score = deterministic_risk["risk_score"]
            ra.risk_level = deterministic_risk["risk_level"]
            ra.risk_factors = deterministic_risk["risk_factors"]
            ra.evidence_ids = deterministic_risk["evidence_ids"]
            ra.scoring_details = deterministic_risk.get("scoring_details", {})
            ra.recommended_action = deterministic_risk["recommended_action"]
            ra.explanation = deterministic_risk["explanation"]
            ra.isolation_forest_score = anomaly_score

        # Create Approval Request if HIGH or CRITICAL
        if deterministic_risk["risk_level"] in ("HIGH", "CRITICAL"):
            app_req_id = f"REQ_{case.id}"
            req_exists = self.db.query(ApprovalRequest).filter(ApprovalRequest.id == app_req_id).first()
            if not req_exists:
                app_req = ApprovalRequest(
                    id=app_req_id,
                    case_id=case.id,
                    action_type=f"EXECUTE_{deterministic_risk['recommended_action']}",
                    status="PENDING",
                    requested_by="Autonomous Response Agent",
                    reason=f"High risk score ({deterministic_risk['risk_score']}) warrants human review before PayPal financial action."
                )
                self.db.add(app_req)

        # Audit Log Entry
        audit = AuditLog(
            id=f"AUD_{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}_{transaction.id}",
            case_id=case.id,
            transaction_id=transaction.id,
            event_type="MULTI_AGENT_INVESTIGATION",
            actor=actor,
            previous_state="UNASSESSED",
            new_state=deterministic_risk["risk_level"],
            api_ref="/api/investigations/run",
            details={
                "risk_score": deterministic_risk["risk_score"],
                "risk_level": deterministic_risk["risk_level"],
                "recommended_action": deterministic_risk["recommended_action"],
                "evidence_count": len(deterministic_risk["evidence_ids"]),
                "cluster_id": matched_cluster.get("id") if matched_cluster else None
            }
        )
        self.db.add(audit)
        self.db.commit()

        return {
            "case_id": case.id,
            "transaction_id": transaction.id,
            "risk_score": deterministic_risk["risk_score"],
            "risk_level": deterministic_risk["risk_level"],
            "recommended_action": deterministic_risk["recommended_action"],
            "approval_status": case.approval_status,
            "cluster": matched_cluster,
            "agent_executions": [
                tx_result, id_result, graph_result, inv_result, risk_result, resp_result
            ]
        }
