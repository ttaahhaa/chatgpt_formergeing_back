"""
Repository for knowledge graph operations.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import uuid
from datetime import datetime

from app.database.models import KnowledgeGraph, KnowledgeGraphNode, KnowledgeGraphEdge
from app.database.config import mongodb_config
from app.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class KnowledgeGraphRepository(BaseRepository[KnowledgeGraph]):
    """Repository for knowledge graph operations."""
    
    def __init__(self):
        """Initialize the knowledge graph repository."""
        super().__init__(
            collection_name=mongodb_config.knowledge_graph_collection,
            model_class=KnowledgeGraph
        )
    
    async def initialize_graph(self, owner_id: Optional[str] = None) -> Optional[str]:
        """
        Initialize a new knowledge graph.
        
        Args:
            owner_id: Optional owner user ID
            
        Returns:
            Graph ID if successful, None otherwise
        """
        try:
            # Check if a graph already exists for this owner
            if owner_id:
                existing = await self.find({"owner_id": owner_id}, limit=1)
                if existing:
                    logger.info(f"Knowledge graph already exists for owner {owner_id}")
                    return existing[0].id
            
            # Generate a unique ID
            graph_id = f"graph_{uuid.uuid4()}"
            
            # Create empty graph
            graph = KnowledgeGraph(
                id=graph_id,
                owner_id=owner_id,
                nodes=[],
                edges=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            return await self.create(graph)
        except Exception as e:
            logger.error(f"Error initializing knowledge graph: {str(e)}")
            return None
    
    async def get_graph(self, owner_id: Optional[str] = None) -> Optional[KnowledgeGraph]:
        """
        Get the knowledge graph for an owner.
        
        Args:
            owner_id: Optional owner user ID
            
        Returns:
            Knowledge graph if found, None otherwise
        """
        query = {}
        if owner_id:
            query["owner_id"] = owner_id
        
        results = await self.find(query, limit=1)
        return results[0] if results else None
    
    async def add_node(self, graph_id: str, label: str, node_type: str = "entity", properties: Dict[str, Any] = None) -> Optional[str]:
        """
        Add a node to the knowledge graph.
        
        Args:
            graph_id: Graph ID
            label: Node label
            node_type: Node type
            properties: Node properties
            
        Returns:
            Node ID if successful, None otherwise
        """
        try:
            # Generate a unique node ID
            node_id = f"node_{uuid.uuid4()}"
            
            # Create node
            node = KnowledgeGraphNode(
                id=node_id,
                label=label,
                type=node_type,
                properties=properties or {}
            )
            
            # Add node to graph
            result = await self.collection.update_one(
                {"_id": graph_id},
                {
                    "$push": {"nodes": node.dict()},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Added node {node_id} to graph {graph_id}")
                return node_id
            
            logger.warning(f"Graph {graph_id} not found or not updated")
            return None
        except Exception as e:
            logger.error(f"Error adding node: {str(e)}")
            return None
    
    async def add_edge(self, graph_id: str, source_id: str, target_id: str, relation: str, properties: Dict[str, Any] = None) -> Optional[str]:
        """
        Add an edge to the knowledge graph.
        
        Args:
            graph_id: Graph ID
            source_id: Source node ID
            target_id: Target node ID
            relation: Edge relation/label
            properties: Edge properties
            
        Returns:
            Edge ID if successful, None otherwise
        """
        try:
            # Generate a unique edge ID
            edge_id = f"edge_{uuid.uuid4()}"
            
            # Create edge
            edge = KnowledgeGraphEdge(
                id=edge_id,
                source=source_id,
                target=target_id,
                relation=relation,
                properties=properties or {}
            )
            
            # Add edge to graph
            result = await self.collection.update_one(
                {"_id": graph_id},
                {
                    "$push": {"edges": edge.dict()},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Added edge {edge_id} to graph {graph_id}")
                return edge_id
            
            logger.warning(f"Graph {graph_id} not found or not updated")
            return None
        except Exception as e:
            logger.error(f"Error adding edge: {str(e)}")
            return None
    
    async def find_node(self, graph_id: str, node_id: str) -> Optional[KnowledgeGraphNode]:
        """
        Find a node in the knowledge graph.
        
        Args:
            graph_id: Graph ID
            node_id: Node ID
            
        Returns:
            Node if found, None otherwise
        """
        try:
            result = await self.collection.find_one(
                {"_id": graph_id, "nodes.id": node_id},
                {"nodes.$": 1}
            )
            
            if result and "nodes" in result and len(result["nodes"]) > 0:
                node_data = result["nodes"][0]
                return KnowledgeGraphNode(**node_data)
            
            return None
        except Exception as e:
            logger.error(f"Error finding node: {str(e)}")
            return None
    
    async def find_nodes_by_label(self, graph_id: str, label: str, limit: int = 10) -> List[KnowledgeGraphNode]:
        """
        Find nodes by label in the knowledge graph.
        
        Args:
            graph_id: Graph ID
            label: Node label to search for
            limit: Maximum number of nodes to return
            
        Returns:
            List of matching nodes
        """
        try:
            # This is a simple pattern matching query
            result = await self.collection.find_one(
                {"_id": graph_id},
                {"nodes": 1}
            )
            
            if not result or "nodes" not in result:
                return []
            
            # Filter nodes by label (case-insensitive partial match)
            matching_nodes = []
            for node_data in result["nodes"]:
                if label.lower() in node_data.get("label", "").lower():
                    matching_nodes.append(KnowledgeGraphNode(**node_data))
                    if len(matching_nodes) >= limit:
                        break
            
            return matching_nodes
        except Exception as e:
            logger.error(f"Error finding nodes by label: {str(e)}")
            return []
    
    async def find_related_nodes(self, graph_id: str, node_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Find nodes directly connected to a given node.
        
        Args:
            graph_id: Graph ID
            node_id: Node ID
            
        Returns:
            Dictionary with incoming and outgoing relations
        """
        try:
            result = await self.collection.find_one(
                {"_id": graph_id},
                {"nodes": 1, "edges": 1}
            )
            
            if not result:
                return {"incoming": [], "outgoing": []}
            
            edges = result.get("edges", [])
            nodes = {node["id"]: node for node in result.get("nodes", [])}
            
            # Find incoming and outgoing edges
            incoming = []
            outgoing = []
            
            for edge in edges:
                if edge["source"] == node_id and edge["target"] in nodes:
                    # Outgoing relation
                    target_node = nodes[edge["target"]]
                    outgoing.append({
                        "node_id": edge["target"],
                        "label": target_node["label"],
                        "relation": edge["relation"],
                        "type": target_node.get("type", "entity")
                    })
                elif edge["target"] == node_id and edge["source"] in nodes:
                    # Incoming relation
                    source_node = nodes[edge["source"]]
                    incoming.append({
                        "node_id": edge["source"],
                        "label": source_node["label"],
                        "relation": edge["relation"],
                        "type": source_node.get("type", "entity")
                    })
            
            return {
                "incoming": incoming,
                "outgoing": outgoing
            }
        except Exception as e:
            logger.error(f"Error finding related nodes: {str(e)}")
            return {"incoming": [], "outgoing": []}
    
    async def clear_graph(self, graph_id: str) -> bool:
        """
        Clear all nodes and edges from a knowledge graph.
        
        Args:
            graph_id: Graph ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"_id": graph_id},
                {
                    "$set": {
                        "nodes": [],
                        "edges": [],
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Cleared graph {graph_id}")
                return True
            
            logger.warning(f"Graph {graph_id} not found or not updated")
            return False
        except Exception as e:
            logger.error(f"Error clearing graph: {str(e)}")
            return False
    
    async def get_graph_stats(self, graph_id: str) -> Dict[str, int]:
        """
        Get statistics about a knowledge graph.
        
        Args:
            graph_id: Graph ID
            
        Returns:
            Dictionary with node and edge counts
        """
        try:
            result = await self.collection.find_one(
                {"_id": graph_id},
                {"nodes": 1, "edges": 1}
            )
            
            if not result:
                return {"nodes": 0, "edges": 0}
            
            return {
                "nodes": len(result.get("nodes", [])),
                "edges": len(result.get("edges", []))
            }
        except Exception as e:
            logger.error(f"Error getting graph stats: {str(e)}")
            return {"nodes": 0, "edges": 0}
