"""Graph-Based Fraud Network Detection.

Goes beyond single-transaction anomalies (IsolationForest) to detect
fraud *networks*: shared PANs, circular payments, vendor clustering.

Uses NetworkX for graph construction and analysis.
"""

from __future__ import annotations

from typing import Any

import networkx as nx


def build_transaction_graph(
    transactions: list[dict[str, Any]],
) -> nx.DiGraph:
    """Build a directed graph from transaction records.

    Nodes: agents, vendors, bank accounts
    Edges: payment flows with amount/frequency metadata
    """
    G = nx.DiGraph()

    for txn in transactions:
        agent = txn.get("agent_id", "unknown_agent")
        vendor = txn.get("vendor_name", txn.get("vendor_id", "unknown_vendor"))
        amount = txn.get("amount_paise", 0)
        bank_account = txn.get("bank_account", "")
        ifsc = txn.get("ifsc", "")
        pan = txn.get("pan", "")

        # Add nodes with metadata
        G.add_node(agent, type="agent")
        G.add_node(vendor, type="vendor")

        if bank_account:
            G.add_node(bank_account, type="bank_account", ifsc=ifsc)
            G.add_edge(vendor, bank_account, relation="owns_account")

        if pan:
            G.add_node(pan, type="pan")
            G.add_edge(vendor, pan, relation="has_pan")

        # Add or update payment edge
        if G.has_edge(agent, vendor):
            G[agent][vendor]["total_paise"] += amount
            G[agent][vendor]["count"] += 1
        else:
            G.add_edge(
                agent, vendor,
                relation="pays",
                total_paise=amount,
                count=1,
            )

    return G


def detect_fraud_patterns(
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run graph-based fraud detection on transaction data.

    Detects:
    1. Shared PAN clusters (multiple vendors, same PAN → shell companies)
    2. High vendor centrality (single vendor receiving from many agents)
    3. Circular payment patterns (A → B → C → A)
    4. Suspiciously concentrated payouts
    """
    if not transactions:
        return {"patterns_found": 0, "risk_level": "low", "findings": []}

    G = build_transaction_graph(transactions)
    findings: list[dict[str, Any]] = []

    # 1. Shared PAN detection
    pan_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "pan"]
    for pan in pan_nodes:
        vendors_with_pan = [
            pred for pred in G.predecessors(pan)
            if G.nodes[pred].get("type") == "vendor"
        ]
        if len(vendors_with_pan) > 1:
            findings.append({
                "type": "shared_pan",
                "severity": "high",
                "description": f"PAN {pan} shared by {len(vendors_with_pan)} vendors",
                "entities": vendors_with_pan,
                "pan": pan,
            })

    # 2. Shared bank account detection
    bank_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "bank_account"]
    for account in bank_nodes:
        vendors_with_account = [
            pred for pred in G.predecessors(account)
            if G.nodes[pred].get("type") == "vendor"
        ]
        if len(vendors_with_account) > 1:
            findings.append({
                "type": "shared_bank_account",
                "severity": "high",
                "description": f"Bank account {account} shared by {len(vendors_with_account)} vendors",
                "entities": vendors_with_account,
            })

    # 3. High centrality detection (vendor receiving from too many agents)
    vendor_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "vendor"]
    if vendor_nodes:
        in_degree = {n: G.in_degree(n) for n in vendor_nodes}
        max_degree = max(in_degree.values()) if in_degree else 0
        if max_degree > 1:
            for vendor, degree in in_degree.items():
                if degree > max(2, len(vendor_nodes) * 0.5):
                    total_received = sum(
                        G[pred][vendor].get("total_paise", 0)
                        for pred in G.predecessors(vendor)
                        if G[pred][vendor].get("relation") == "pays"
                    )
                    findings.append({
                        "type": "high_centrality",
                        "severity": "medium",
                        "description": f"Vendor '{vendor}' receives from {degree} agents",
                        "vendor": vendor,
                        "agent_count": degree,
                        "total_received_paise": total_received,
                    })

    # 4. Cycle detection (circular payments)
    try:
        payment_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("relation") == "pays"]
        payment_graph = G.edge_subgraph(payment_edges) if payment_edges else nx.DiGraph()
        cycles = list(nx.simple_cycles(payment_graph))
        for cycle in cycles[:5]:  # Limit to first 5
            findings.append({
                "type": "circular_payment",
                "severity": "critical",
                "description": f"Circular payment pattern detected: {' → '.join(cycle)}",
                "entities": cycle,
            })
    except nx.NetworkXError:
        pass

    # Aggregate risk level
    severity_weights = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    total_risk = sum(severity_weights.get(f["severity"], 0) for f in findings)

    if total_risk >= 5:
        risk_level = "critical"
    elif total_risk >= 3:
        risk_level = "high"
    elif total_risk >= 1:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "patterns_found": len(findings),
        "risk_level": risk_level,
        "total_risk_score": total_risk,
        "graph_stats": {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "agents": len([n for n, d in G.nodes(data=True) if d.get("type") == "agent"]),
            "vendors": len(vendor_nodes),
        },
        "findings": findings,
    }
