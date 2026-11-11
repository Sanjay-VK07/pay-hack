import math
import networkx as nx
from typing import Dict, List, Any, Optional, Set, Tuple
from sqlalchemy.orm import Session
from app.models.models import (
    CustomerAccount, Transaction, Device, PaymentIdentity,
    TransactionIndicator, FraudCluster, InvestigationCase
)

class GraphIntelligenceEngine:
    def __init__(self, db: Session):
        self.db = db
        self.G = nx.Graph()

    def build_graph(self) -> nx.Graph:
        self.G.clear()
        
        # 1. Add Customer Account Nodes (Canonical ID: acc.id)
        accounts = self.db.query(CustomerAccount).all()
        for acc in accounts:
            is_high_risk = acc.risk_rating in ("HIGH", "CRITICAL")
            self.G.add_node(
                acc.id,
                node_id=acc.id,
                label=acc.full_name,
                type="ACCOUNT",
                email=acc.email,
                risk_score=None,
                risk_level=acc.risk_rating,
                account_number=acc.account_number,
                country=acc.country,
                status=acc.status,
                entity="account"
            )

        # 2. Add Device Nodes (Canonical ID: dev.id)
        devices = self.db.query(Device).all()
        for dev in devices:
            is_dev_suspicious = dev.is_emulator or dev.risk_level in ("HIGH", "CRITICAL")
            self.G.add_node(
                dev.id,
                node_id=dev.id,
                label=f"Device: {dev.device_fingerprint[:12]}",
                type="DEVICE",
                fingerprint=dev.device_fingerprint,
                device_type=dev.device_type,
                os=dev.os,
                browser=dev.browser,
                is_emulator=dev.is_emulator,
                risk_score=None,
                risk_level=dev.risk_level,
                entity="device"
            )

        # 3. Add Payment Identity Nodes (Canonical ID: pident.id)
        identities = self.db.query(PaymentIdentity).all()
        for pident in identities:
            is_pid_flagged = bool(pident.risk_flags)
            self.G.add_node(
                pident.id,
                node_id=pident.id,
                label=f"Identity: {pident.masked_value}",
                type="PAYMENT_IDENTITY",
                identity_type=pident.identity_type,
                masked_value=pident.masked_value,
                risk_score=None,
                risk_level="HIGH" if is_pid_flagged else "LOW",
                entity="payment_identity"
            )

        # 4. Add Transactions and Construct Explicit Edges
        transactions = self.db.query(Transaction).all()
        ip_nodes_added: Set[str] = set()

        for txn in transactions:
            txn_node_key = txn.id
            is_txn_critical = txn.risk_category in ("HIGH", "CRITICAL")
            
            # Lookup linked investigation if any
            inv_case = self.db.query(InvestigationCase).filter(InvestigationCase.primary_transaction_id == txn.id).first()
            case_ref = inv_case.id if inv_case else None

            self.G.add_node(
                txn_node_key,
                node_id=txn.id,
                label=f"Txn ${txn.amount:.2f}",
                type="TRANSACTION",
                amount=txn.amount,
                currency=txn.currency,
                payment_status=txn.payment_status,
                risk_score=txn.risk_score,
                risk_level=txn.risk_category,
                investigation_status=txn.investigation_status,
                case_ref=case_ref,
                timestamp=txn.timestamp.isoformat() if txn.timestamp else "",
                entity="transaction"
            )

            # Edge: Account MADE Transaction
            acc_node_key = txn.customer_id
            if self.G.has_node(acc_node_key):
                owns_suspicious = is_txn_critical
                owns_reason = f"Transaction record references account {acc_node_key}."
                self.G.add_edge(
                    acc_node_key,
                    txn_node_key,
                    relationship="ACCOUNT_MADE_TRANSACTION",
                    weight=1.0,
                    supporting_evidence=f"The transaction record references customer account {acc_node_key}.",
                    alternative_explanation="A stored account-to-transaction link does not establish who authorized the purchase.",
                    evidence_id=f"EV_MADE_{txn.id}",
                    is_suspicious=owns_suspicious,
                    suspicious_reason=owns_reason,
                    timestamp=txn.timestamp.isoformat() if txn.timestamp else ""
                )

            # Edge & Node: IP Indicator
            if txn.ip_address:
                ip_node_key = f"IP_{txn.ip_address.replace('.', '_')}"
                is_proxy_ip = txn.ip_address in ("185.220.101.5", "45.154.255.88")
                
                if ip_node_key not in ip_nodes_added:
                    self.G.add_node(
                        ip_node_key,
                        node_id=txn.ip_address,
                        label=f"IP: {txn.ip_address}",
                        type="IP_INDICATOR",
                        ip_address=txn.ip_address,
                        risk_score=None,
                        risk_level="HIGH" if is_proxy_ip else "LOW",
                        is_proxy=is_proxy_ip,
                        entity="ip"
                    )
                    ip_nodes_added.add(ip_node_key)

                self.G.add_edge(
                    txn_node_key,
                    ip_node_key,
                    relationship="TRANSACTION_ORIGINATES_FROM_IP",
                    weight=1.0,
                    supporting_evidence=f"The transaction record stores IP address {txn.ip_address}; no live network or threat-intelligence check was performed.",
                    alternative_explanation="Shared residential ISP, corporate VPN, or university NAT gateway may legitimately pool users under this IP.",
                    evidence_id=f"EV_IP_{txn.id}",
                    is_suspicious=is_proxy_ip,
                    suspicious_reason=f"IP matched a configured demo rule ({txn.ip_address}); this is not a live reputation check." if is_proxy_ip else "IP address is present in the local transaction record; reputation was not checked.",
                    shared_indicator=txn.ip_address
                )
                
                if self.G.has_node(acc_node_key):
                    self.G.add_edge(
                        acc_node_key,
                        ip_node_key,
                        relationship="ACCOUNT_SHARES_IP_INDICATOR",
                        weight=0.8,
                        supporting_evidence=f"Local transaction records link this account with IP {txn.ip_address}; no live network or reputation check was performed.",
                        alternative_explanation="Shared IP addresses alone do not constitute conclusive proof of fraud; multiple distinct users may share public Wi-Fi or carrier-grade NAT.",
                        evidence_id=f"EV_ACC_IP_{txn.customer_id}_{txn.ip_address}",
                        is_suspicious=is_proxy_ip,
                        suspicious_reason=f"IP matched a configured demo rule ({txn.ip_address}); this is not a live reputation check." if is_proxy_ip else "IP address is present in the local transaction record; reputation was not checked.",
                        shared_indicator=txn.ip_address
                    )

            # Edge: Account & Transaction USES Device
            if txn.device_id:
                dev_node_key = txn.device_id
                dev_model = self.db.query(Device).filter(Device.id == txn.device_id).first()
                is_emul = dev_model.is_emulator if dev_model else False
                
                if self.G.has_node(dev_node_key):
                    self.G.add_edge(
                        txn_node_key,
                        dev_node_key,
                        relationship="TRANSACTION_EXECUTED_ON_DEVICE",
                        weight=1.0,
                        supporting_evidence=f"Linked device record is marked emulator ({dev_model.device_fingerprint[:8]}); no independent hardware sensor check was performed." if is_emul else "Transaction references a device record not marked as an emulator; physical hardware was not independently verified.",
                        alternative_explanation="Legitimate developer testing on emulator or secondary family device.",
                        evidence_id=f"EV_DEV_{txn.id}",
                        is_suspicious=is_emul,
                        suspicious_reason=f"Linked demo device record is marked emulator ({dev_model.device_fingerprint[:8]})." if is_emul else "Linked device record is not marked as an emulator; hardware was not independently verified.",
                        shared_indicator=dev_model.device_fingerprint if dev_model else ""
                    )
                    if self.G.has_node(acc_node_key):
                        # Check if device is shared across multiple accounts
                        shared_owners = self.db.query(Transaction.customer_id).filter(
                            Transaction.device_id == dev_node_key,
                            Transaction.customer_id != acc_node_key
                        ).distinct().count()
                        
                        dev_is_shared = shared_owners > 0
                        dev_susp = is_emul or dev_is_shared
                        dev_reason = (
                            f"Local transaction records reference device fingerprint '{dev_model.device_fingerprint[:8]}' from {shared_owners + 1} account profiles."
                            + (" The linked demo device record is marked as an emulator; hardware was not independently verified." if is_emul else "")
                        ) if dev_susp else "No shared-device or emulator flag is recorded in this local dataset."

                        self.G.add_edge(
                            acc_node_key,
                            dev_node_key,
                            relationship="ACCOUNT_USES_DEVICE",
                            weight=1.5,
                            supporting_evidence=dev_reason,
                            alternative_explanation="Household sharing a family desktop or tablet. Look for matching surnames or delivery addresses.",
                            evidence_id=f"EV_ACC_DEV_{txn.customer_id}_{txn.device_id}",
                            is_suspicious=dev_susp,
                            suspicious_reason=dev_reason,
                            shared_indicator=dev_model.device_fingerprint if dev_model else ""
                        )

            # Edge: Account & Transaction USES Payment Identity
            if txn.payment_identity_id:
                pid_node_key = txn.payment_identity_id
                pid_model = self.db.query(PaymentIdentity).filter(PaymentIdentity.id == txn.payment_identity_id).first()
                has_flags = bool(pid_model.risk_flags) if pid_model else False

                if self.G.has_node(pid_node_key):
                    self.G.add_edge(
                        txn_node_key,
                        pid_node_key,
                        relationship="TRANSACTION_USES_PAYMENT_IDENTITY",
                        weight=1.0,
                        supporting_evidence=f"Local payment identity record contains demo risk flags: {', '.join(pid_model.risk_flags)}." if has_flags else "Transaction references this local payment identity record; no credential verification was performed.",
                        alternative_explanation="Authorized employee using corporate procurement card.",
                        evidence_id=f"EV_PID_{txn.id}",
                        is_suspicious=has_flags,
                        suspicious_reason=f"Local payment identity record contains demo risk flags: {', '.join(pid_model.risk_flags)}." if has_flags else "No credential risk flag is stored in this local record; external status was not checked.",
                        shared_indicator=pid_model.masked_value if pid_model else ""
                    )
                    if self.G.has_node(acc_node_key):
                        shared_pid_owners = self.db.query(Transaction.customer_id).filter(
                            Transaction.payment_identity_id == pid_node_key,
                            Transaction.customer_id != acc_node_key
                        ).distinct().count()

                        pid_is_shared = shared_pid_owners > 0
                        pid_susp = has_flags or pid_is_shared
                        pid_reason = (
                            f"Local transaction records link payment identity '{pid_model.masked_value}' to {shared_pid_owners + 1} customer profiles."
                            + (f" Risk tags: {', '.join(pid_model.risk_flags)}." if has_flags else "")
                        ) if pid_susp else "Payment identity not shared in the local dataset"

                        self.G.add_edge(
                            acc_node_key,
                            pid_node_key,
                            relationship="ACCOUNT_SHARES_PAYMENT_IDENTITY",
                            weight=2.0,
                            supporting_evidence=pid_reason,
                            alternative_explanation="Shared corporate credit card or authorized family members under joint account.",
                            evidence_id=f"EV_ACC_PID_{txn.customer_id}_{txn.payment_identity_id}",
                            is_suspicious=pid_susp,
                            suspicious_reason=pid_reason,
                            shared_indicator=pid_model.masked_value if pid_model else ""
                        )

        return self.G

    def detect_fraud_clusters(self) -> List[Dict[str, Any]]:
        """
        Identify connected components and isolate clusters sharing critical fraud vectors:
        - Multiple accounts sharing the same physical device or emulator.
        - Multiple accounts sharing payment identities (stolen card hashes, payment accounts).
        - Shared suspicious IP proxies with velocity spikes.
        All stats are derived from actual NetworkX graph data.
        """
        if not self.G or self.G.number_of_nodes() == 0:
            self.build_graph()

        clusters = []
        components = list(nx.connected_components(self.G))

        for idx, comp in enumerate(components):
            subgraph = self.G.subgraph(comp)
            
            # Count entities in component
            accounts = [n for n in comp if self.G.nodes[n].get("type") == "ACCOUNT"]
            transactions = [n for n in comp if self.G.nodes[n].get("type") == "TRANSACTION"]
            devices = [n for n in comp if self.G.nodes[n].get("type") == "DEVICE"]
            identities = [n for n in comp if self.G.nodes[n].get("type") == "PAYMENT_IDENTITY"]
            ips = [n for n in comp if self.G.nodes[n].get("type") == "IP_INDICATOR"]

            # Multi-account sharing test
            shared_devices = []
            for dev in devices:
                neighbors = [nbr for nbr in self.G.neighbors(dev) if self.G.nodes[nbr].get("type") == "ACCOUNT"]
                if len(neighbors) > 1:
                    shared_devices.append((dev, [self.G.nodes[nbr]["node_id"] for nbr in neighbors]))

            shared_identities = []
            for pid in identities:
                neighbors = [nbr for nbr in self.G.neighbors(pid) if self.G.nodes[nbr].get("type") == "ACCOUNT"]
                if len(neighbors) > 1:
                    shared_identities.append((pid, [self.G.nodes[nbr]["node_id"] for nbr in neighbors]))

            is_coordinated = len(shared_devices) > 0 or len(shared_identities) > 0

            # Calculate cluster metrics
            total_amount = sum(self.G.nodes[t].get("amount", 0.0) for t in transactions)
            flagged_transaction_value = sum(
                self.G.nodes[t].get("amount", 0.0) for t in transactions 
                if self.G.nodes[t].get("risk_level") in ("HIGH", "CRITICAL")
            )
            scores = [
                self.G.nodes[n].get("risk_score")
                for n in transactions
                if isinstance(self.G.nodes[n].get("risk_score"), (int, float))
            ]
            avg_score = sum(scores) / len(scores) if scores else 0.0
            max_score = max(scores) if scores else 0.0

            # Count supporting evidence edges
            suspicious_edges_count = sum(
                1 for u, v, d in subgraph.edges(data=True) if d.get("is_suspicious")
            )

            cluster_risk = max_score

            cluster_id = f"CLUSTER_{idx + 1:03d}"

            # Tag nodes in graph with cluster_id
            for node_name in comp:
                self.G.nodes[node_name]["cluster_id"] = cluster_id

            cluster_type = "ISOLATED_ACTIVITY"
            if len(shared_devices) > 0 and len(shared_identities) > 0:
                cluster_type = "SHARED_DEVICE_AND_IDENTITY_GROUP"
            elif len(shared_devices) > 0:
                cluster_type = "SHARED_DEVICE_GROUP"
            elif len(shared_identities) > 0:
                cluster_type = "SHARED_IDENTITY_GROUP"
            elif len(accounts) > 1:
                cluster_type = "MULTI_ACCOUNT_GROUP"

            summary = (
                f"Cluster {cluster_id} contains {len(accounts)} accounts, {len(transactions)} transactions, "
                f"with ${total_amount:.2f} total transaction value (${flagged_transaction_value:.2f} value from transactions flagged by local rules). "
                + (f"Local records share {len(shared_devices)} device record(s) and {len(shared_identities)} payment-identity record(s); this is a review signal, not proof of coordination." if is_coordinated else "No shared device or payment-identity record was found in this component.")
            )

            clusters.append({
                "id": cluster_id,
                "name": f"{cluster_type.replace('_', ' ').title()} #{idx+1}",
                "cluster_type": cluster_type,
                "risk_score": round(cluster_risk, 1),
                "risk_level": "CRITICAL" if cluster_risk >= 85 else ("HIGH" if cluster_risk >= 65 else ("MEDIUM" if cluster_risk >= 40 else "LOW")),
                "is_coordinated": is_coordinated,
                "member_accounts_count": len(accounts),
                "member_transactions_count": len(transactions),
                "member_devices_count": len(devices),
                "shared_identities_count": len(shared_identities),
                "shared_devices_count": len(shared_devices),
                "total_transaction_value": round(total_amount, 2),
                "suspicious_financial_exposure": round(flagged_transaction_value, 2),
                "total_exposure": round(total_amount, 2),
                "evidence_count": suspicious_edges_count,
                "summary": summary,
                "account_ids": [self.G.nodes[a]["node_id"] for a in accounts],
                "transaction_ids": [self.G.nodes[t]["node_id"] for t in transactions]
            })

        # Sort clusters by risk score descending
        clusters.sort(key=lambda x: x["risk_score"], reverse=True)
        return clusters

    def to_react_flow(self, filter_cluster_id: Optional[str] = None, filter_node_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Convert NetworkX graph into clean JSON compatible with React Flow,
        using an advanced force-directed layout with collision detection.
        Includes connected entities, suspicious relationship reasons, and forensic evidence.
        """
        if not self.G or self.G.number_of_nodes() == 0:
            self.build_graph()
            self.detect_fraud_clusters()

        selected_nodes = set(self.G.nodes())
        if filter_cluster_id and filter_cluster_id != 'ALL':
            selected_nodes = {n for n in selected_nodes if self.G.nodes[n].get("cluster_id") == filter_cluster_id}
        elif filter_node_id:
            # Include 2-hop neighborhood of selected node
            target_key = filter_node_id if self.G.has_node(filter_node_id) else None
            if not target_key:
                for n, attrs in self.G.nodes(data=True):
                    if attrs.get("node_id") == filter_node_id:
                        target_key = n
                        break
            if target_key:
                one_hop = set(self.G.neighbors(target_key))
                two_hop = set()
                for neighbor in one_hop:
                    two_hop.update(self.G.neighbors(neighbor))
                selected_nodes = {target_key} | one_hop | two_hop

        subgraph = self.G.subgraph(selected_nodes)
        total_n = len(selected_nodes)

        # Force-directed layout computation via NetworkX spring_layout with high separation
        k_factor = max(4.0, 6.5 / math.sqrt(max(1, total_n)))
        pos_raw = nx.spring_layout(
            subgraph,
            k=k_factor,
            iterations=350,
            scale=1600.0,
            center=(900.0, 560.0),
            seed=42
        )

        # Keep the seeded force layout stable, then separate overlapping node
        # rectangles. React Flow fits the resulting bounds after data arrives.
        nodes_sorted = sorted(list(selected_nodes))
        positions: Dict[str, Dict[str, float]] = {}
        for idx, n in enumerate(nodes_sorted):
            p = pos_raw[n]
            # Layer nodes vertically by entity type to prevent visual collision
            type_offset_y = 0.0
            node_type = self.G.nodes[n].get("type", "")
            if node_type == "ACCOUNT":
                type_offset_y = -130.0
            elif node_type == "TRANSACTION":
                type_offset_y = 130.0
            elif node_type == "DEVICE":
                type_offset_y = -260.0
            elif node_type == "PAYMENT_IDENTITY":
                type_offset_y = 260.0
            elif node_type == "IP_INDICATOR":
                type_offset_y = 0.0

            positions[n] = {
                "x": float(p[0]) + (idx % 4) * 20.0,
                "y": float(p[1]) + type_offset_y
            }

        # Generous collision avoidance gutters for clear node separation
        min_dist_x = 280.0
        min_dist_y = 175.0
        for _ in range(120):
            moved = False
            for i, n1 in enumerate(nodes_sorted):
                for j in range(i + 1, len(nodes_sorted)):
                    n2 = nodes_sorted[j]
                    dx = positions[n2]["x"] - positions[n1]["x"]
                    dy = positions[n2]["y"] - positions[n1]["y"]
                    if dx == 0 and dy == 0:
                        # Stable, ID-derived direction for exact overlaps.
                        dx = 1.0 if (i + j) % 2 == 0 else -1.0
                        dy = 1.0
                    if abs(dx) < min_dist_x and abs(dy) < min_dist_y:
                        overlap_x = min_dist_x - abs(dx)
                        overlap_y = min_dist_y - abs(dy)
                        if overlap_x <= overlap_y:
                            push = (overlap_x / 2.0) + 1.0
                            direction = 1.0 if dx >= 0 else -1.0
                            positions[n2]["x"] += direction * push
                            positions[n1]["x"] -= direction * push
                        else:
                            push = (overlap_y / 2.0) + 1.0
                            direction = 1.0 if dy >= 0 else -1.0
                            positions[n2]["y"] += direction * push
                            positions[n1]["y"] -= direction * push
                        moved = True
            if not moved:
                break

        nodes_list = []
        for node_key in nodes_sorted:
            data = self.G.nodes[node_key]
            
            # Compute connected neighbors and suspicious reasons for this node
            connected_entities = []
            suspicious_connections = []
            for neighbor in self.G.neighbors(node_key):
                nbr_data = self.G.nodes[neighbor]
                edge_data = self.G.get_edge_data(node_key, neighbor) or {}
                rel = edge_data.get("relationship", "CONNECTED_TO")
                reason = edge_data.get("suspicious_reason", "")
                is_susp = edge_data.get("is_suspicious", False)
                ev_id = edge_data.get("evidence_id")

                connected_entities.append({
                    "node_id": nbr_data.get("node_id", neighbor),
                    "key": neighbor,
                    "label": nbr_data.get("label", neighbor),
                    "type": nbr_data.get("type", "UNKNOWN"),
                    "relationship": rel,
                    "risk_level": nbr_data.get("risk_level", "LOW"),
                    "evidence_id": ev_id,
                    "suspicious_reason": reason
                })

                if is_susp:
                    suspicious_connections.append({
                        "connected_to": nbr_data.get("label", neighbor),
                        "relationship": rel,
                        "reason": reason,
                        "evidence_id": ev_id
                    })

            nodes_list.append({
                "id": node_key,
                "label": data.get("label", node_key),
                "type": data.get("type", "ACCOUNT"),
                "risk_score": data.get("risk_score", 0.0),
                "risk_level": data.get("risk_level", "LOW"),
                "cluster_id": data.get("cluster_id"),
                "position": {"x": round(positions[node_key]["x"], 1), "y": round(positions[node_key]["y"], 1)},
                "connected_entities": connected_entities,
                "suspicious_connections": suspicious_connections,
                "attributes": {
                    k: v for k, v in data.items() 
                    if k not in ("label", "type", "risk_score", "risk_level", "cluster_id")
                }
            })

        edges_list = []
        edge_id_counter = 1
        for u, v, data in self.G.edges(data=True):
            if u in selected_nodes and v in selected_nodes:
                edges_list.append({
                    "id": f"e_{edge_id_counter}_{u}_{v}",
                    "source": u,
                    "target": v,
                    "relationship": data.get("relationship", "RELATED"),
                    "evidence_id": data.get("evidence_id"),
                    "is_suspicious": data.get("is_suspicious", False),
                    "suspicious_reason": data.get("suspicious_reason", ""),
                    "supporting_evidence": data.get("supporting_evidence", data.get("suspicious_reason", "")),
                    "alternative_explanation": data.get("alternative_explanation", ""),
                    "timestamp": data.get("timestamp"),
                    "shared_indicator": data.get("shared_indicator"),
                    "attributes": {
                        "weight": data.get("weight", 1.0),
                        "relationship": data.get("relationship", "RELATED"),
                        "is_suspicious": data.get("is_suspicious", False),
                        "suspicious_reason": data.get("suspicious_reason", ""),
                        }
                })
                edge_id_counter += 1

        clusters = self.detect_fraud_clusters()

        return {
            "nodes": nodes_list,
            "edges": edges_list,
            "clusters": clusters,
            "total_nodes": len(nodes_list),
            "total_edges": len(edges_list),
            "summary": {
                "total_graph_nodes": self.G.number_of_nodes(),
                "total_graph_edges": self.G.number_of_edges(),
                "clusters_count": len(clusters),
                "active_filter_cluster": filter_cluster_id
            }
        }
