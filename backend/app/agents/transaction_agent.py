from typing import Dict, Any
from app.agents.base_agent import BaseAgent

class TransactionIntelligenceAgent(BaseAgent):
    name: str = "Transaction Intelligence Agent"
    stage: str = "TRANSACTION_INTEL"
    description: str = "Analyzes transaction velocity, value spikes, merchant profile, and temporal anomalies."

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        transaction = inputs.get("transaction", {})
        customer = inputs.get("customer", {})
        prior_failed_count = inputs.get("prior_failed_count", 0)
        recent_count = inputs.get("recent_count", 0)

        amount = transaction.get("amount", 0.0)
        currency = transaction.get("currency", "USD")

        # Deterministic evaluation
        anomalies = []
        if amount > 1500.0:
            anomalies.append(f"High-value payment of ${amount:.2f} exceeds standard $1,500 threshold.")
        elif amount > 700.0:
            anomalies.append(f"Elevated transaction amount: ${amount:.2f}.")

        if prior_failed_count >= 2:
            anomalies.append(f"Detected {prior_failed_count} immediate prior failed transactions (card testing indicator).")

        if recent_count >= 3:
            anomalies.append(f"Extreme transaction velocity: {recent_count} transactions within 60 minutes.")

        # Attempt LLM refinement if available
        llm_response = None
        if self.has_llm:
            prompt = f"Analyze transaction {transaction.get('id')} of amount {amount} {currency}. Anomalies noted: {anomalies}. Account: {customer.get('full_name')}."
            system = "You are a FinTech Transaction Intelligence Agent. Provide a concise JSON analysis with keys: summary, anomalies (list), confidence_score (float 0-1)."
            llm_response = self._call_llm_if_available(prompt, system)

        if llm_response and "summary" in llm_response:
            return {
                "is_llm_generated": True,
                "summary": llm_response.get("summary"),
                "confidence_score": llm_response.get("confidence_score", 0.94),
                "findings": {
                    "amount_analysis": f"${amount:.2f} {currency}",
                    "velocity_window_count": recent_count,
                    "failed_attempts": prior_failed_count,
                    "anomalies": llm_response.get("anomalies", anomalies)
                }
            }

        # Deterministic Expert Output
        summary = (
            f"Evaluated transaction of ${amount:.2f} {currency}. "
            + (f"Flagged {len(anomalies)} behavioral anomalies: {'; '.join(anomalies)}." if anomalies else "Transaction velocity and amount within legitimate baseline thresholds.")
        )

        return {
            "is_llm_generated": False,
            "summary": summary,
            "confidence_score": 0.96 if anomalies else 0.98,
            "findings": {
                "amount_analysis": f"${amount:.2f} {currency}",
                "velocity_window_count": recent_count,
                "failed_attempts": prior_failed_count,
                "anomalies": anomalies
            }
        }
