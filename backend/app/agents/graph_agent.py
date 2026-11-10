from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent

class GraphIntelligenceAgent(BaseAgent):
    name: str = "Graph Intelligence Agent"
    stage: str = "GRAPH_INTEL"
    description: str = "Analyzes entity relationship graphs via NetworkX, uncovering coordinated clusters, device collisions, and multi-hop fraud rings."

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        cluster_info = inputs.get("cluster_info") or {}
        related_accounts = inputs.get("related_accounts") or []
        shared_devices = inputs.get("shared_devices") or []
        shared_identities = inputs.get("shared_identities") or []
        two_hop_count = inputs.get("two_hop_count", 0)
        total_cluster_exposure = inputs.get("total_cluster_exposure", 0.0)

        cluster_id = cluster_info.get("id", "UNCLUSTERED")
        cluster_type = cluster_info.get("cluster_type", "ISOLATED_ACTIVITY")
        is_coordinated = cluster_info.get("is_coordinated", False) or len(related_accounts) > 1

        graph_anomalies: List[str] = []
        if is_coordinated:
            graph_anomalies.append(
                f"Multi-entity collision: NetworkX graph traversal discovered cluster {cluster_id} "
                f"spanning {len(related_accounts)} accounts connected through shared infrastructure."
            )
        if len(shared_devices) > 0:
            graph_anomalies.append(f"Hardware graph collision: {len(shared_devices)} device node(s) shared across disjoint account entities.")
        if len(shared_identities) > 0:
            graph_anomalies.append(f"Payment credential collision: {len(shared_identities)} payment identity node(s) reused across accounts.")
        if two_hop_count > 4:
            graph_anomalies.append(f"Dense two-hop graph neighborhood ({two_hop_count} connected nodes) indicating organized syndicate structure.")

        # Attempt LLM graph reasoning if available
        llm_response = None
        if self.has_llm:
            prompt = (
                f"Analyze graph cluster {cluster_id} ({cluster_type}). "
                f"Accounts: {len(related_accounts)}, Shared Devices: {len(shared_devices)}, Shared Identities: {len(shared_identities)}, "
                f"Two-Hop Size: {two_hop_count}, Financial Exposure: ${total_cluster_exposure:.2f}. "
                f"Anomalies: {graph_anomalies}."
            )
            system = "You are a FinTech Graph Intelligence Agent. Provide a concise JSON analysis with keys: summary, topology_risk (string), confidence_score (float 0-1)."
            llm_response = self._call_llm_if_available(prompt, system)

        if llm_response and "summary" in llm_response:
            return {
                "is_llm_generated": True,
                "summary": llm_response.get("summary"),
                "confidence_score": llm_response.get("confidence_score", 0.95),
                "findings": {
                    "cluster_id": cluster_id,
                    "cluster_type": cluster_type,
                    "is_coordinated": is_coordinated,
                    "member_accounts_count": len(related_accounts),
                    "shared_devices_count": len(shared_devices),
                    "shared_identities_count": len(shared_identities),
                    "two_hop_neighborhood_size": two_hop_count,
                    "total_cluster_exposure": total_cluster_exposure,
                    "topology_risk": llm_response.get("topology_risk", "HIGH_DENSITY_COORDINATION"),
                    "graph_anomalies": graph_anomalies
                }
            }

        # Deterministic Expert Output
        summary = (
            f"NetworkX graph analysis for cluster {cluster_id}. "
            + (f"Coordinated syndicate topology detected: {'; '.join(graph_anomalies)}" if graph_anomalies else "Isolated transaction node with no suspicious entity sharing.")
        )

        return {
            "is_llm_generated": False,
            "summary": summary,
            "confidence_score": 0.97 if is_coordinated else 0.99,
            "findings": {
                "cluster_id": cluster_id,
                "cluster_type": cluster_type,
                "is_coordinated": is_coordinated,
                "member_accounts_count": len(related_accounts),
                "shared_devices_count": len(shared_devices),
                "shared_identities_count": len(shared_identities),
                "two_hop_neighborhood_size": two_hop_count,
                "total_cluster_exposure": total_cluster_exposure,
                "topology_risk": "COORDINATED_FRAUD_RING" if is_coordinated else "ISOLATED_LEGITIMATE",
                "graph_anomalies": graph_anomalies
            }
        }
