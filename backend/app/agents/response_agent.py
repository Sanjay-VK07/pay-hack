from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent

class ResponseAgent(BaseAgent):
    name: str = "Response Planning Agent"
    stage: str = "RESPONSE"
    description: str = "Formulates authorized mitigation workflows with mandatory human approval gating."

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        risk_findings = inputs.get("risk_findings") or {}
        transaction = inputs.get("transaction") or {}
        approval_status = inputs.get("approval_status", "PENDING")

        risk_level = risk_findings.get("risk_level", "LOW")
        recommended_action = risk_findings.get("recommended_action", "ALLOW")
        amount = transaction.get("amount", 0.0)
        currency = transaction.get("currency", "USD")

        requires_human_approval = risk_level in ("HIGH", "CRITICAL")
        workflow_steps: List[str] = []

        if risk_level == "CRITICAL":
            workflow_steps.append("Review the linked transaction, identity, and graph records with an investigator.")
            workflow_steps.append(f"If a captured payment is confirmed, consider a refund of ${amount:.2f} {currency} after authorized human review.")
            workflow_steps.append("No account lock, watchlist update, notification, or payment action is performed by this recommendation.")
        elif risk_level == "HIGH":
            workflow_steps.append("Request investigator review of the stored transaction and identity records.")
            workflow_steps.append("Consider step-up verification or additional documentation if supported by the merchant workflow.")
        elif risk_level == "MEDIUM":
            workflow_steps.append("Review the recorded signals; no transaction permission or account setting is changed by this recommendation.")
        else:
            workflow_steps.append("No local rule triggered a review recommendation. This does not verify the transaction as legitimate.")

        summary = (
            f"Response mitigation plan: {recommended_action}."
            + (" Requires authorized human review and separate payment eligibility checks before any financial action." if requires_human_approval else " This recommendation does not change transaction or account state.")
        )

        return {
            "is_llm_generated": False,
            "summary": summary,
            "findings": {
                "action": recommended_action,
                "risk_level": risk_level,
                "requires_human_approval": requires_human_approval,
                "approval_status": approval_status,
                "execution_authorized": False,
                "workflow_steps": workflow_steps
            }
        }
