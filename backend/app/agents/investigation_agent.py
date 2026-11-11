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
                f"Local graph records include this activity in the {cluster_type} group ({cluster_info.get('name')}) with {member_count} linked customer accounts; association is a review signal, not proof of fraud."
            )
            evidence_synthesis.append(
                f"Recorded transaction value in the linked group totals ${total_exposure:.2f}; this is not a verified loss amount."
            )
        else:
            evidence_synthesis.append("Transaction graph indicates isolated execution pattern with no active syndicate links.")

        if id_findings.get("is_emulator"):
            evidence_synthesis.append("The linked local device record is marked as an emulator; no independent hardware check was performed.")

        # Attempt LLM synthesis if available
        llm_response = None
        if self.has_llm:
            provider_context = {
                "cluster_type": cluster_type,
                "linked_account_count": member_count,
                "recorded_transaction_value": total_exposure,
                "graph_link_present": bool(is_coordinated),
                "transaction_signal_count": len(tx_findings.get("anomalies", [])),
                "identity_signal_count": len(id_findings.get("identity_flags", [])),
                "local_review_signals": evidence_synthesis,
            }
            prompt = f"Summarize these local investigation signals only: {provider_context}. State uncertainty and do not infer guilt, verified loss, or evidence not supplied."
            system = "You are a Lead Fraud Investigation Agent. Use only supplied signals, never invent evidence, and distinguish a local association from proof. Return JSON: summary, evidence_synthesis (list)."
            llm_response = self._call_llm_if_available(prompt, system)

        if llm_response and "summary" in llm_response:
            return {
                "is_llm_generated": True,
                "summary": llm_response.get("summary"),
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
            f"Local graph review found a {cluster_type} pattern. "
            + (f"The linked records include {member_count} accounts and ${total_exposure:.2f} in recorded transaction value. These associations require analyst review." if is_coordinated else "No multi-account link pattern was detected in the available local records.")
        )

        return {
            "is_llm_generated": False,
            "summary": summary,
            "findings": {
                "cluster_id": cluster_info.get("id"),
                "cluster_type": cluster_type,
                "is_coordinated": is_coordinated,
                "linked_accounts_count": member_count,
                "total_network_exposure": f"${total_exposure:.2f}",
                "evidence_synthesis": evidence_synthesis
            }
        }
