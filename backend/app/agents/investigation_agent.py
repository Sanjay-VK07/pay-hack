from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent

class FraudInvestigationAgent(BaseAgent):
    name: str = "Fraud Investigation Agent"
    stage: str = "FRAUD_INVESTIGATION"
    description: str = "Corroborates graph topology, multi-account clusters, and coordinated fraud patterns."

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        cluster_info = inputs.get("cluster_info") or {}
        tx_findings = inputs.get("transaction_findings") or {}
        id_findings = inputs.get("identity_findings") or {}
        related_accounts = inputs.get("related_accounts") or []

        is_coordinated = cluster_info.get("is_coordinated", False)
        cluster_type = cluster_info.get("cluster_type", "ISOLATED")
        member_count = cluster_info.get("member_accounts_count", 1)
        total_exposure = cluster_info.get("total_exposure", 0.0)

        evidence_synthesis: List[str] = []
        if is_coordinated:
            evidence_synthesis.append(
                f"Graph analysis confirmed active membership in {cluster_type} ({cluster_info.get('name')}) linking {member_count} customer accounts."
            )
            evidence_synthesis.append(
                f"Financial exposure across coordinated ring totals ${total_exposure:.2f} across shared hardware & card identities."
            )
        else:
            evidence_synthesis.append("Transaction graph indicates isolated execution pattern with no active syndicate links.")

        if id_findings.get("is_emulator"):
            evidence_synthesis.append("Confirmed automated bot/emulator runtime signature.")

        # Attempt LLM synthesis if available
        llm_response = None
        if self.has_llm:
            prompt = (
                f"Investigate fraud ring: Cluster {cluster_info.get('name')} with {member_count} accounts, "
                f"${total_exposure} exposure. Txn findings: {tx_findings}. Identity findings: {id_findings}."
            )
            system = "You are a Lead Fraud Investigation Agent. Synthesize graph and identity evidence into JSON: summary, evidence_synthesis (list), confidence_score (float 0-1)."
            llm_response = self._call_llm_if_available(prompt, system)

        if llm_response and "summary" in llm_response:
            return {
                "is_llm_generated": True,
                "summary": llm_response.get("summary"),
                "confidence_score": llm_response.get("confidence_score", 0.96),
                "findings": {
                    "cluster_id": cluster_info.get("id"),
                    "cluster_type": cluster_type,
                    "is_coordinated": is_coordinated,
                    "linked_accounts_count": member_count,
                    "total_network_exposure": f"${total_exposure:.2f}",
                    "evidence_synthesis": llm_response.get("evidence_synthesis", evidence_synthesis)
                }
            }

        # Deterministic Expert Output
        summary = (
            f"Multi-Agent investigation confirmed {cluster_type} pattern. "
            + (f"Network consists of {member_count} coordinated accounts with ${total_exposure:.2f} exposure. Corroborated cross-account fraud indicators." if is_coordinated else "No multi-account fraud ring topology detected.")
        )

        return {
            "is_llm_generated": False,
            "summary": summary,
            "confidence_score": 0.97 if is_coordinated else 0.99,
            "findings": {
                "cluster_id": cluster_info.get("id"),
                "cluster_type": cluster_type,
                "is_coordinated": is_coordinated,
                "linked_accounts_count": member_count,
                "total_network_exposure": f"${total_exposure:.2f}",
                "evidence_synthesis": evidence_synthesis
            }
        }
