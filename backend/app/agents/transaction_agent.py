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
            provider_context = {
                "amount": amount,
                "currency": currency,
                "recent_transaction_count": recent_count,
                "prior_failed_count": prior_failed_count,
                "rule_signals": anomalies,
            }
            prompt = f"Summarize these local transaction signals only: {provider_context}. Do not infer customer identity, intent, or facts that are not provided."
            system = "You are a FinTech Transaction Intelligence Agent. Use only supplied signals and do not invent evidence. Return JSON with keys: summary, anomalies (list)."
            llm_response = self._call_llm_if_available(prompt, system)

        if llm_response and "summary" in llm_response:
            return {
                "is_llm_generated": True,
                "summary": llm_response.get("summary"),
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
            + (f"Flagged {len(anomalies)} rule-based review signals: {'; '.join(anomalies)}." if anomalies else "No configured amount or velocity rule triggered; this does not establish that the transaction is legitimate.")
        )

        return {
            "is_llm_generated": False,
            "summary": summary,
            "findings": {
                "amount_analysis": f"${amount:.2f} {currency}",
                "velocity_window_count": recent_count,
                "failed_attempts": prior_failed_count,
                "anomalies": anomalies
            }
        }
