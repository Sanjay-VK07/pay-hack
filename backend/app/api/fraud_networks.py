from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.graph.graph_service import GraphIntelligenceEngine
from app.schemas.schemas import GraphDataResponse

router = APIRouter(prefix="/fraud-networks", tags=["Fraud Networks"])

@router.get("", response_model=GraphDataResponse)
def get_fraud_networks(
    cluster_id: Optional[str] = Query(None),
    node_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    engine = GraphIntelligenceEngine(db)
    graph_data = engine.to_react_flow(filter_cluster_id=cluster_id, filter_node_id=node_id)
    return graph_data

@router.get("/{cluster_id}")
def get_cluster_details(cluster_id: str, db: Session = Depends(get_db)):
    engine = GraphIntelligenceEngine(db)
    clusters = engine.detect_fraud_clusters()
    match = next((c for c in clusters if c["id"] == cluster_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    subgraph_data = engine.to_react_flow(filter_cluster_id=cluster_id)
    return {
        "cluster": match,
        "graph": subgraph_data
    }
