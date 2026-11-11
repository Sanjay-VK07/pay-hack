from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent

class GraphIntelligenceAgent(BaseAgent):
    name: str = "Graph Intelligence Agent"
    stage: str = "GRAPH_INTEL"
    description: str = "Summarizes local entity relationships from transaction, device, and payment-identity records."

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
                f"Local graph traversal found a linked activity group spanning {len(related_accounts)} account records."
            )
        if len(shared_devices) > 0:
            graph_anomalies.append(f"Local records link {len(shared_devices)} device node(s) with multiple account records; ownership is not established.")
        if len(shared_identities) > 0:
            graph_anomalies.append(f"Local records link {len(shared_identities)} payment identity node(s) with multiple accounts; authorization is not established.")
        if two_hop_count > 4:
            graph_anomalies.append(f"The local graph has a two-hop neighborhood of {two_hop_count} connected records; this alone does not establish coordination.")

        # Attempt LLM graph reasoning if available
        llm_response = None
        if self.has_llm:
            prompt = (
                f"Analyze graph cluster {cluster_id} ({cluster_type}). "
                f"Accounts: {len(related_accounts)}, Shared Devices: {len(shared_devices)}, Shared Identities: {len(shared_identities)}, "
                f"Two-Hop Size: {two_hop_count}, Financial Exposure: ${total_cluster_exposure:.2f}. "
                f"Anomalies: {graph_anomalies}."
            )
            system = "You are a FinTech Graph Intelligence Agent. Provide a concise JSON analysis with keys: summary, topology_risk (string)."
            llm_response = self._call_llm_if_available(prompt, system)

        if llm_response and "summary" in llm_response:
            return {
                "is_llm_generated": True,
                "summary": llm_response.get("summary"),
                "findings": {
                    "cluster_id": cluster_id,
                    "cluster_type": cluster_type,
                    "is_coordinated": is_coordinated,
                    "member_accounts_count": len(related_accounts),
                    "shared_devices_count": len(shared_devices),
                    "shared_identities_count": len(shared_identities),
                    "two_hop_neighborhood_size": two_hop_count,
                    "total_cluster_exposure": total_cluster_exposure,
                    "topology_risk": llm_response.get("topology_risk", "LINKED_ACTIVITY_FOR_REVIEW"),
                    "graph_anomalies": graph_anomalies
                }
            }

        # Deterministic Expert Output
        summary = (
            f"NetworkX graph analysis for cluster {cluster_id}. "
            + (f"Local relationships for analyst review: {'; '.join(graph_anomalies)}" if graph_anomalies else "No linked-entity pattern was found in the available local records.")
        )

        return {
            "is_llm_generated": False,
            "summary": summary,
            "findings": {
                "cluster_id": cluster_id,
                "cluster_type": cluster_type,
                "is_coordinated": is_coordinated,
                "member_accounts_count": len(related_accounts),
                "shared_devices_count": len(shared_devices),
                "shared_identities_count": len(shared_identities),
                "two_hop_neighborhood_size": two_hop_count,
                "total_cluster_exposure": total_cluster_exposure,
                "topology_risk": "LINKED_ACTIVITY_FOR_REVIEW" if is_coordinated else "NO_LOCAL_LINK_PATTERN_FOUND",
                "graph_anomalies": graph_anomalies
            }
        }
