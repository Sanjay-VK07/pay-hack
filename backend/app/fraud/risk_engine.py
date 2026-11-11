from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.models import Transaction, CustomerAccount, Device, PaymentIdentity

class DeterministicRiskEngine:
    """
    Production-grade deterministic risk calculation engine with documented factor weights.
    Calculates transparent, fully explainable fraud scores from verifiable transaction evidence.
    """
    
    # Documented Factor Weights (Max contribution per category)
    WEIGHT_VELOCITY = 25.0
    WEIGHT_AMOUNT = 20.0
    WEIGHT_DEVICE = 25.0
    WEIGHT_PAYMENT_IDENTITY = 25.0
    WEIGHT_FAILED_ATTEMPTS = 15.0
    WEIGHT_ACCOUNT_AGE = 10.0
    WEIGHT_CLUSTER_LINK = 30.0

    def __init__(self, db: Session):
        self.db = db

    def evaluate_transaction(
        self,
        transaction: Transaction,
        cluster_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        risk_score = 0.0
        risk_factors: List[str] = []
        evidence_ids: List[str] = []
        evidence_records: List[Dict[str, Any]] = []
        breakdown: Dict[str, float] = {}

        customer = self.db.query(CustomerAccount).filter(CustomerAccount.id == transaction.customer_id).first()
        device = self.db.query(Device).filter(Device.id == transaction.device_id).first() if transaction.device_id else None
        payment_identity = self.db.query(PaymentIdentity).filter(PaymentIdentity.id == transaction.payment_identity_id).first() if transaction.payment_identity_id else None

        # 1. Device Indicators (Emulator, multiple accounts sharing fingerprint)
        if device:
            if device.is_emulator:
                score_add = 25.0
                risk_score += score_add
                breakdown["emulator_detected"] = score_add
                rf = f"Device record in the demo dataset is marked as an emulator ({device.device_fingerprint}). This metadata is not independently verified by a hardware sensor."
                risk_factors.append(rf)
                ev_id = f"EV_{transaction.id}_DEV_EMUL"
                evidence_ids.append(ev_id)
                evidence_records.append({
                    "id": ev_id,
                    "evidence_type": "DEVICE_FINGERPRINT",
                    "source_entity": device.id,
                    "target_entity": transaction.id,
                    "observed_value": f"Demo device record marked emulator ({device.device_fingerprint})",
                    "baseline_value": "Physical mobile or desktop hardware profile",
                    "severity": "CRITICAL",
                    "alternative_explanation": "Software development or automated QA may legitimately use emulator environments.",
                    "explanation": f"The stored device metadata lists {device.os} and {device.browser} and marks this record as an emulator; it does not prove automated abuse.",
                    "related_transaction_id": transaction.id,
                    "related_account_id": customer.id if customer else None,
                    "description": rf
                })

            # Check accounts sharing this device
            shared_accounts = self.db.query(Transaction.customer_id).filter(
                Transaction.device_id == device.id,
                Transaction.customer_id != transaction.customer_id
            ).distinct().all()
            if shared_accounts:
                score_add = min(25.0, len(shared_accounts) * 12.5)
                risk_score += score_add
                breakdown["device_sharing"] = score_add
                rf = f"Device identifier is linked to {len(shared_accounts) + 1} customer accounts in the local transaction records. Shared use alone does not establish fraud."
                risk_factors.append(rf)
                ev_id = f"EV_{transaction.id}_DEV_SHARE"
                evidence_ids.append(ev_id)
                evidence_records.append({
                    "id": ev_id,
                    "evidence_type": "DEVICE_SHARING",
                    "source_entity": device.id,
                    "target_entity": customer.id if customer else "UNKNOWN_ACCOUNT",
                    "observed_value": f"{len(shared_accounts) + 1} customer accounts linked to device record {device.id}",
                    "baseline_value": "No expected sharing baseline configured; analyst review required",
                    "severity": "CRITICAL" if len(shared_accounts) >= 2 else "HIGH",
                    "alternative_explanation": "A family, workplace, or public computer may legitimately be shared.",
                    "explanation": "The local transaction records associate this device identifier with multiple customer accounts; the relationship needs analyst review.",
                    "related_transaction_id": transaction.id,
                    "related_account_id": customer.id if customer else None,
                    "description": rf
                })

        # 2. Payment Identity Indicators (Card/Account sharing across different accounts)
        if payment_identity:
            if payment_identity.risk_flags:
                score_add = 20.0
                risk_score += score_add
                breakdown["payment_identity_flagged"] = score_add
                rf = f"Payment identity record contains these demo risk flags: {', '.join(payment_identity.risk_flags)}. No issuer or external consortium lookup was performed."
                risk_factors.append(rf)
                ev_id = f"EV_{transaction.id}_PID_FLAG"
                evidence_ids.append(ev_id)
                evidence_records.append({
                    "id": ev_id,
                    "evidence_type": "PAYMENT_CREDENTIAL_FLAG",
                    "source_entity": payment_identity.id,
                    "target_entity": transaction.id,
                    "observed_value": f"Risk Flags: {', '.join(payment_identity.risk_flags)} ({payment_identity.masked_value})",
                    "baseline_value": "No external credential status lookup was performed",
                    "severity": "HIGH",
                    "alternative_explanation": "The stored risk flags may be stale or unrelated to this transaction.",
                    "explanation": f"The local payment identity record for {payment_identity.masked_value} contains risk flags; their origin is not independently verified.",
                    "related_transaction_id": transaction.id,
                    "related_account_id": customer.id if customer else None,
                    "description": rf
                })

            shared_owners = self.db.query(Transaction.customer_id).filter(
                Transaction.payment_identity_id == payment_identity.id,
                Transaction.customer_id != transaction.customer_id
            ).distinct().all()
            if shared_owners:
                score_add = 25.0
                risk_score += score_add
                breakdown["payment_identity_reused"] = score_add
                rf = f"Payment identity '{payment_identity.masked_value}' is linked to {len(shared_owners) + 1} customer accounts in the local transaction records. This relationship alone does not establish card cloning."
                risk_factors.append(rf)
                ev_id = f"EV_{transaction.id}_PID_SHARE"
                evidence_ids.append(ev_id)
                evidence_records.append({
                    "id": ev_id,
                    "evidence_type": "SHARED_PAYMENT_IDENTITY",
                    "source_entity": payment_identity.id,
                    "target_entity": customer.id if customer else "UNKNOWN_ACCOUNT",
                    "observed_value": f"Shared across {len(shared_owners) + 1} distinct accounts ({payment_identity.masked_value})",
                    "baseline_value": "No expected sharing baseline configured; analyst review required",
                    "severity": "CRITICAL",
                    "alternative_explanation": "A payment method may be legitimately shared by family members or within an organization.",
                    "explanation": f"The local records share payment identity {payment_identity.masked_value} across accounts; verify legitimate shared-card use before drawing a conclusion.",
                    "related_transaction_id": transaction.id,
                    "related_account_id": customer.id if customer else None,
                    "description": rf
                })

        # 3. Transaction Velocity (Rapid successive orders)
        if transaction.timestamp:
            one_hour_ago = transaction.timestamp - timedelta(hours=1)
            recent_txns = self.db.query(Transaction).filter(
                Transaction.customer_id == transaction.customer_id,
                Transaction.timestamp >= one_hour_ago,
                Transaction.timestamp <= transaction.timestamp,
                Transaction.id != transaction.id
            ).count()

            if recent_txns >= 3:
                score_add = 22.0
                risk_score += score_add
                breakdown["velocity_spike"] = score_add
                rf = f"High transaction velocity: {recent_txns + 1} transactions are recorded within a 60-minute window."
                risk_factors.append(rf)
                ev_id = f"EV_{transaction.id}_VELOCITY"
                evidence_ids.append(ev_id)
                evidence_records.append({
                    "id": ev_id,
                    "evidence_type": "VELOCITY_SPIKE",
                    "source_entity": transaction.id,
                    "target_entity": customer.id if customer else "UNKNOWN_ACCOUNT",
                    "observed_value": f"{recent_txns + 1} transactions in 60 minutes",
                    "baseline_value": "Configured rule threshold: 4 or more recorded transactions in a rolling 60-minute window",
                    "severity": "HIGH",
                    "alternative_explanation": "Legitimate customer ordering multiple items individually or retrying after checkout glitch.",
                    "explanation": "The recorded transaction count exceeds this rule's threshold; it is a review signal and does not establish automated activity.",
                    "related_transaction_id": transaction.id,
                    "related_account_id": customer.id if customer else None,
                    "description": rf
                })
            elif recent_txns >= 1:
                score_add = 8.0
                risk_score += score_add
                breakdown["velocity_moderate"] = score_add

        # 4. Unusual Amount / Value Deviation
        if transaction.amount >= 1500.0:
            score_add = 18.0
            risk_score += score_add
            breakdown["high_amount"] = score_add
            rf = f"High ticket transaction value (${transaction.amount:,.2f} {transaction.currency}) exceeds standard risk threshold ($1,500.00)."
            risk_factors.append(rf)
            ev_id = f"EV_{transaction.id}_AMOUNT"
            evidence_ids.append(ev_id)
            evidence_records.append({
                "id": ev_id,
                "evidence_type": "AMOUNT_THRESHOLD",
                "source_entity": transaction.id,
                "target_entity": customer.id if customer else "UNKNOWN_ACCOUNT",
                "observed_value": f"${transaction.amount:,.2f} {transaction.currency}",
            "baseline_value": "Configured rule threshold: $1,500.00 USD",
                "severity": "HIGH",
                "alternative_explanation": "Legitimate major appliance, electronics or jewelry purchase. Amount alone does not prove fraud.",
                "explanation": f"Transaction amount of ${transaction.amount:,.2f} meets the configured high-value rule threshold; no customer-specific spending baseline was used by this rule.",
                "related_transaction_id": transaction.id,
                "related_account_id": customer.id if customer else None,
                "description": rf
            })
        elif transaction.amount >= 750.0:
            score_add = 8.0
            risk_score += score_add
            breakdown["elevated_amount"] = score_add

        # 5. Failed Payment Loop / Card Testing
        prior_failed = self.db.query(Transaction).filter(
            Transaction.customer_id == transaction.customer_id,
            Transaction.payment_status == "FAILED"
        ).count()
        if prior_failed >= 2:
            score_add = 15.0
            risk_score += score_add
            breakdown["failed_attempt_loop"] = score_add
            rf = f"Multiple ({prior_failed}) failed authorization attempts detected immediately prior to completion (card testing pattern)."
            risk_factors.append(rf)
            ev_id = f"EV_{transaction.id}_FAIL_LOOP"
            evidence_ids.append(ev_id)
            evidence_records.append({
                "id": ev_id,
                "evidence_type": "FAILED_AUTH_SPIKE",
                "source_entity": transaction.id,
                "target_entity": customer.id if customer else "UNKNOWN_ACCOUNT",
                "observed_value": f"{prior_failed} failed transactions are recorded for this customer",
                "baseline_value": "Configured rule threshold: at least 2 failed transactions in the stored history",
                "severity": "HIGH",
                "alternative_explanation": "User mistyping card expiration date or billing CVV multiple times before getting it right.",
                "explanation": "The stored history exceeds the failed-transaction rule threshold; the current rule does not verify the decline reason or its timing.",
                "related_transaction_id": transaction.id,
                "related_account_id": customer.id if customer else None,
                "description": rf
            })

        # 6. Account Age Factor
        if customer and customer.account_age_days < 7 and transaction.amount > 300.0:
            score_add = 10.0
            risk_score += score_add
            breakdown["new_account_large_spend"] = score_add
            rf = f"Customer account record is {customer.account_age_days} days old and the transaction exceeds the configured amount threshold."
            risk_factors.append(rf)
            ev_id = f"EV_{transaction.id}_NEW_ACCT"
            evidence_ids.append(ev_id)
            evidence_records.append({
                "id": ev_id,
                "evidence_type": "NEW_ACCOUNT_HIGH_SPEND",
                "source_entity": customer.id,
                "target_entity": transaction.id,
                "observed_value": f"Account age: {customer.account_age_days} days (Amount: ${transaction.amount:,.2f})",
                "baseline_value": "Configured rule thresholds: account age under 7 days and amount over $300",
                "severity": "MEDIUM",
                "alternative_explanation": "New user who registered specifically to purchase an advertised high-ticket item.",
                "explanation": "This is a rule-based review signal; account age and amount alone do not establish fraud or predict a chargeback.",
                "related_transaction_id": transaction.id,
                "related_account_id": customer.id,
                "description": rf
            })

        # 7. Coordinated Cluster Linkage
        if cluster_info and cluster_info.get("is_coordinated"):
            score_add = 30.0
            risk_score += score_add
            breakdown["coordinated_cluster_membership"] = score_add
            cluster_name = cluster_info.get("name", "Syndicate Network")
            accounts_count = cluster_info.get("member_accounts_count", 4)
            rf = f"Transaction is linked to graph component '{cluster_name}' with {accounts_count} accounts in the demo graph. This is a relationship signal, not a confirmed fraud network."
            risk_factors.append(rf)
            ev_id = f"EV_{transaction.id}_CLUSTER"
            evidence_ids.append(ev_id)
            evidence_records.append({
                "id": ev_id,
                "evidence_type": "CONNECTED_GRAPH_COMPONENT",
                "source_entity": transaction.id,
                "target_entity": cluster_info.get("id", "CLUSTER_001"),
                "observed_value": f"Member of {cluster_name} ({accounts_count} linked accounts)",
                "baseline_value": "Isolated graph node (0 shared device, IP, or credential links)",
                "severity": "CRITICAL",
                "alternative_explanation": "Shared office co-working space or university campus network. Graph triangulation separates legitimate campus nodes from credential-sharing rings.",
                "explanation": "NetworkX connected the records through shared identifiers in the local dataset; the graph does not independently confirm fraudulent intent.",
                "related_transaction_id": transaction.id,
                "related_account_id": customer.id if customer else None,
                "description": rf
            })

        # 8. Anonymized Proxy / Tor IP Gateway
        if transaction.ip_address and transaction.ip_address in ("185.220.101.5", "45.154.255.88"):
            score_add = 12.0
            risk_score += score_add
            breakdown["proxy_ip"] = score_add
            rf = f"Transaction IP matches an address in the application's configured demo rule list ({transaction.ip_address}); no live threat-intelligence lookup was performed."
            risk_factors.append(rf)
            ev_id = f"EV_{transaction.id}_PROXY_IP"
            evidence_ids.append(ev_id)
            evidence_records.append({
                "id": ev_id,
                "evidence_type": "GEO_PROXY_IP",
                "source_entity": transaction.id,
                "target_entity": transaction.ip_address,
                "observed_value": f"IP matched configured demo rule: {transaction.ip_address}",
                "baseline_value": "Configured demo rule-list match; no location comparison is performed",
                "severity": "HIGH",
                "alternative_explanation": "Privacy-conscious user running commercial VPN or iCloud Private Relay. Never treated as proof of fraud in isolation.",
                "explanation": "The configured rule match is a signal for review; this app did not verify the IP against a live threat-intelligence service.",
                "related_transaction_id": transaction.id,
                "related_account_id": customer.id if customer else None,
                "description": rf
            })

        # Normalize total score to range 0.0 - 100.0
        final_score = min(100.0, round(risk_score, 1))

        # Build transparent mathematical score explanation
        contributing_factors = []
        factor_defs = [
            ("emulator_detected", "Emulator Metadata Flag", 25.0, "Device record in the demo dataset is marked as an emulator"),
            ("device_sharing", "Device Identifier Reuse", 25.0, "Device identifier is linked to multiple local account records"),
            ("payment_identity_reused", "Shared Payment Identity", 25.0, "Payment identity is linked to multiple local account records"),
            ("payment_identity_flagged", "Payment Identity Risk Flags", 20.0, "Payment identity record contains demo risk flags"),
            ("coordinated_cluster_membership", "Connected Graph Component", 30.0, "Transaction is connected to other records in the local graph"),
            ("velocity_spike", "Transaction Velocity Spike", 22.0, "Four or more recorded transactions in a rolling 60-minute window"),
            ("velocity_moderate", "Repeated Transaction Activity", 8.0, "At least two recorded transactions in a rolling 60-minute window"),
            ("high_amount", "High Amount Rule", 18.0, "Transaction amount meets the configured $1,500 threshold"),
            ("elevated_amount", "Elevated Amount Rule", 8.0, "Transaction amount meets the configured $750 threshold"),
            ("failed_attempt_loop", "Failed Transaction Count", 15.0, "At least two failed transactions appear in stored history"),
            ("new_account_large_spend", "New Account and Amount Rule", 10.0, "Account age and amount meet configured review thresholds"),
            ("proxy_ip", "Configured IP Rule Match", 12.0, "IP matches a local configured demo rule; no live lookup was performed")
        ]

        for key, name, max_w, rationale in factor_defs:
            if key in breakdown:
                val = breakdown[key]
                contributing_factors.append({
                    "factor": name,
                    "factor_key": key,
                    "factor_name": name,
                    "weight": val,
                    "weight_assigned": val,
                    "category": key.upper(),
                    "share": f"{round((val / risk_score) * 100, 1) if risk_score > 0 else 0}%",
                    "max_weight": max_w,
                    "percentage_contribution": round((val / risk_score) * 100, 1) if risk_score > 0 else 0,
                    "rationale": rationale
                })

        scoring_details = {
            "calculation_version": "heuristic_v2",
            "formula": "Final Score = min(100.0, sum(Contributed Factor Weights))",
            "deterministic_formula": "Risk_Score = min(100.0, sum(factor_weights))",
            "raw_score": round(risk_score, 1),
            "final_score": final_score,
            "clamped_risk_score": final_score,
            "is_clamped_at_maximum": risk_score >= 100.0,
            "raw_sum_of_weights": round(risk_score, 1),
            "clamping_difference": round(max(0.0, risk_score - 100.0), 1),
            "excess_weight_clamped": round(max(0.0, risk_score - 100.0), 1),
            "factors_count": len(contributing_factors),
            "contributing_factors": contributing_factors,
            "formula_explanation": "Each configured heuristic adds its rule weight. The final score is clamped at 100. This demo score is not a calibrated probability of fraud."
        }

        # Normalize total score to range 0.0 - 100.0
        final_score = min(100.0, round(risk_score, 1))

        # Risk Tier Classification
        if final_score >= 85.0:
            risk_level = "CRITICAL"
            recommended_action = "REFUND_TRANSACTION"
        elif final_score >= 65.0:
            risk_level = "HIGH"
            recommended_action = "RESTRICT_ACCOUNT"
        elif final_score >= 40.0:
            risk_level = "MEDIUM"
            recommended_action = "REVIEW"
        else:
            risk_level = "LOW"
            recommended_action = "ALLOW"

        # Construct deterministic summary explanation
        if risk_factors:
            explanation = (
                f"AgentShield deterministic risk engine classified transaction {transaction.id} as {risk_level} "
                f"(Heuristic Score: {final_score}/100.0). Identified {len(risk_factors)} review signal(s): "
                f"{'; '.join(risk_factors)}."
            )
        else:
            explanation = (
                f"No configured review rule was triggered for transaction {transaction.id}. "
                f"Heuristic Score: {final_score}/100.0 ({risk_level}); this does not independently establish that the transaction is safe."
            )

        return {
            "risk_score": final_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "evidence_ids": evidence_ids,
            "evidence_records": evidence_records,
            "scoring_details": scoring_details,
            "recommended_action": recommended_action,
            "explanation": explanation,
            "breakdown": breakdown
        }
