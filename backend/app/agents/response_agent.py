from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent

class ResponseAgent(BaseAgent):
    name: str = "Autonomous Response Agent"
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
            workflow_steps.append("1. Place immediate temporary lock on customer account credentials.")
            workflow_steps.append(f"2. Stage PayPal Sandbox Refund of ${amount:.2f} {currency} pending human approval.")
            workflow_steps.append("3. Flag hardware fingerprint across Global Watchlist.")
            workflow_steps.append("4. Issue forensic alert to Chief Risk Officer.")
        elif risk_level == "HIGH":
            workflow_steps.append("1. Route transaction to Human Investigator queue.")
            workflow_steps.append("2. Enforce 2FA/Step-up verification on next checkout attempt.")
            workflow_steps.append("3. Request manual receipt and device identification review.")
        elif risk_level == "MEDIUM":
            workflow_steps.append("1. Permit transaction execution under heightened anomaly monitoring.")
            workflow_steps.append("2. Increment risk counter on customer account profile.")
        else:
            workflow_steps.append("1. Clear transaction for standard merchant settlement.")
            workflow_steps.append("2. Record verified legitimate baseline event.")

        # If already approved by human investigator
        execution_authorized = False
        if approval_status == "APPROVED" and risk_level == "CRITICAL":
            workflow_steps.append("✓ Human Approval Granted: Authorized for automated PayPal refund execution.")
            execution_authorized = True

        summary = (
            f"Response mitigation plan: {recommended_action}."
            + (" Requires explicit Human-in-the-Loop approval before PayPal financial refund execution." if requires_human_approval and approval_status != "APPROVED" else " Automated workflow cleared.")
        )

        return {
            "is_llm_generated": False,
            "summary": summary,
            "confidence_score": 0.99,
            "findings": {
                "action": recommended_action,
                "risk_level": risk_level,
                "requires_human_approval": requires_human_approval,
                "approval_status": approval_status,
                "execution_authorized": execution_authorized,
                "workflow_steps": workflow_steps
            }
        }
