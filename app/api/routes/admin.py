"""
Admin routes: clear operations, index rebuilding, and knowledge graph management.
"""
import logging
import re
from typing import List
from collections import Counter
from fastapi import APIRouter, Form, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import (
    get_current_user, check_permission, get_vector_store,
    get_document_repo, get_embedding_repo
)
from app.database.repositories.factory import repository_factory
from app.utils.jwt_utils import TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["admin"])

@router.post("/clear_documents")
async def clear_documents(vector_store = Depends(get_vector_store)):
    """Clear all documents from the system."""
    try:
        # Use the vector store's clear method
        success = await vector_store.async_store.clear()
        
        if success:
            logger.info("Successfully cleared all documents")
            return {"message": "Successfully cleared all documents"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to clear documents"}
            )
    
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Invalid operation error: {str(e)}"}
        )

@router.post("/clear_cache")
async def clear_cache():
    """Clear application cache."""
    try:
        # In MongoDB implementation, this might clear any temporary caches
        # For example, vector store calculation caches, etc.
        logger.info("Clearing application cache")
        
        # This is a placeholder - implement specific cache clearing as needed
        result = True
        
        if result:
            return {"message": "Cache cleared successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to clear cache"}
            )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Cache operation error: %s", str(e))
        return JSONResponse(
            status_code=503,
            content={"error": f"Cache operation error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid cache data: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Invalid cache data: {str(e)}"}
        )

@router.post("/rebuild_index")
async def rebuild_faiss_index(vector_store = Depends(get_vector_store)):
    """Rebuild the FAISS index used for vector similarity search."""
    try:
        # Get async store from sync wrapper
        async_store = vector_store.async_store
        
        # Rebuild index
        success = await async_store.initialize_faiss_index(force_rebuild=True)
        
        if success:
            logger.info("FAISS index rebuilt successfully")
            return {"message": "FAISS index rebuilt successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to rebuild FAISS index"}
            )
    
    except (ConnectionError, RuntimeError, ValueError) as e:
        logger.error("Error rebuilding FAISS index: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Error rebuilding FAISS index: {str(e)}"}
        )

@router.post("/knowledge_graph/build")
async def build_knowledge_graph(
    user_id: str = Form(None),
    document_repo = Depends(get_document_repo)
):
    """Build or rebuild the knowledge graph from documents."""
    try:
        # Get knowledge graph repository
        kg_repo = repository_factory.knowledge_graph_repository
        
        # Initialize or get existing graph
        graph_id = await kg_repo.initialize_graph(owner_id=user_id)
        if not graph_id:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to initialize knowledge graph"}
            )
        
        # Clear existing graph data
        await kg_repo.clear_graph(graph_id)
        
        # Get documents to process
        if user_id:
            documents = await document_repo.find_accessible(user_id)
        else:
            documents = await document_repo.find({})
        
        # Process documents to build the graph
        node_count = 0
        edge_count = 0
        
        for doc in documents:
            # Add document as a node
            doc_node_id = await kg_repo.add_node(
                graph_id=graph_id,
                label=doc.filename,
                node_type="document",
                properties={"id": doc.id, "type": doc.metadata.get("type", "unknown")}
            )
            
            if doc_node_id:
                node_count += 1
                
                # Process document content
                keywords = extract_sample_keywords(doc.content)
                
                for keyword in keywords:
                    # Add keyword as a node
                    keyword_node_id = await kg_repo.add_node(
                        graph_id=graph_id,
                        label=keyword,
                        node_type="keyword"
                    )
                    
                    if keyword_node_id:
                        node_count += 1
                        
                        # Add relationship between document and keyword
                        edge_id = await kg_repo.add_edge(
                            graph_id=graph_id,
                            source_id=doc_node_id,
                            target_id=keyword_node_id,
                            relation="contains"
                        )
                        
                        if edge_id:
                            edge_count += 1
        
        # Get final graph stats
        stats = await kg_repo.get_graph_stats(graph_id)
        
        logger.info("Knowledge graph built with %d nodes and %d edges", stats.get('nodes', 0), stats.get('edges', 0))
        
        return {
            "message": "Knowledge graph built successfully",
            "graph_id": graph_id,
            "stats": stats
        }
    
    except (ValueError, AttributeError) as e:
        logger.error("Invalid graph data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid graph data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@router.get("/knowledge_graph/stats")
async def get_knowledge_graph_stats(user_id: str = Form(None)):
    """Get statistics about the knowledge graph."""
    try:
        # Get knowledge graph repository
        kg_repo = repository_factory.knowledge_graph_repository
        
        # Get or initialize graph
        graph = await kg_repo.get_graph(owner_id=user_id)
        if not graph:
            return {
                "nodes": 0,
                "edges": 0,
                "message": "Knowledge graph not found or empty"
            }
        
        # Get graph stats
        stats = await kg_repo.get_graph_stats(graph.id)
        
        return stats
    
    except (ValueError, AttributeError) as e:
        logger.error("Invalid graph data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid graph data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

# Helper function for keyword extraction (simplified)
def extract_sample_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """Extract sample keywords from text (simplified)."""
    # This is just a simple implementation for demonstration
    # In a real system, use proper NLP techniques
    words = text.lower().split()
    word_freq = {}
    
    for word in words:
        # Skip short words and common stop words
        if len(word) <= 3 or word in ["the", "and", "for", "with", "that", "this"]:
            continue
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    
    # Return top keywords
    return [word for word, _ in sorted_words[:max_keywords]]