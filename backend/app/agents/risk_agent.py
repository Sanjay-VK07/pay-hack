from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent

class RiskAssessmentAgent(BaseAgent):
    name: str = "Risk Assessment Agent"
    stage: str = "RISK_ASSESSMENT"
    description: str = "Synthesizes multi-agent evidence and deterministic risk scores into an explainable verdict."

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        deterministic_risk = inputs.get("deterministic_risk") or {}
        anomaly_score = inputs.get("anomaly_score", 0.0)
        investigation_findings = inputs.get("investigation_findings") or {}

        # Strictly preserve the deterministic score and risk level
        risk_score = deterministic_risk.get("risk_score", 0.0)
        risk_level = deterministic_risk.get("risk_level", "LOW")
        recommended_action = deterministic_risk.get("recommended_action", "ALLOW")
        risk_factors = deterministic_risk.get("risk_factors", [])
        evidence_ids = deterministic_risk.get("evidence_ids", [])

        # Attempt LLM explainability if configured
        explanation = deterministic_risk.get("explanation", "")
        llm_response = None
        if self.has_llm:
            prompt = (
                f"Explain this uncalibrated heuristic review score ({risk_score}/100, {risk_level}) and recommendation "
                f"({recommended_action}) using only these rule factors: {risk_factors}; anomaly signal: {anomaly_score}; "
                f"local investigation summary: {investigation_findings.get('evidence_synthesis')}. "
                "Do not infer a probability, identity, intent, or independent verification."
            )
            system = (
                "You are a FinTech Risk Assessment Agent. Use only the supplied local signals, do not invent evidence, and do not change the score. "
                "Return JSON with keys: executive_explanation."
            )
            llm_response = self._call_llm_if_available(prompt, system)

        if llm_response and "executive_explanation" in llm_response:
            explanation = llm_response.get("executive_explanation")
            return {
                "is_llm_generated": True,
                "summary": explanation,
                "findings": {
                    "validated_risk_score": risk_score,
                    "risk_level": risk_level,
                    "recommended_action": recommended_action,
                    "anomaly_detection_score": anomaly_score,
                    "risk_factors": risk_factors,
                    "evidence_ids": evidence_ids,
                    "executive_explanation": explanation
                }
            }

        return {
            "is_llm_generated": False,
            "summary": explanation,
            "findings": {
                "validated_risk_score": risk_score,
                "risk_level": risk_level,
                "recommended_action": recommended_action,
                "anomaly_detection_score": anomaly_score,
                "risk_factors": risk_factors,
                "evidence_ids": evidence_ids,
                "executive_explanation": explanation
            }
        }
