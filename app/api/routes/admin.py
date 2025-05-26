"""
Admin routes: clear operations, index rebuilding, and knowledge graph management.
"""
import logging
import re
from typing import List, Optional
from collections import Counter
from fastapi import APIRouter, Form, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.dependencies import (
    get_current_user, check_permission, get_vector_store,
    get_document_repo, get_embedding_repo
)
from app.database.repositories.factory import repository_factory
from app.utils.jwt_utils import TokenData
from app.utils.text_processing import extract_sample_keywords

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["admin"])

class KnowledgeGraphBuildRequest(BaseModel):
    user_id: Optional[str] = None

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
    request: KnowledgeGraphBuildRequest,
    document_repo = Depends(get_document_repo)
):
    """Build or rebuild the knowledge graph from documents."""
    try:
        logger.info("Starting knowledge graph build process")
        logger.info(f"Request user_id: {request.user_id}")
        
        # Get knowledge graph repository
        logger.info("Getting knowledge graph repository")
        kg_repo = repository_factory.knowledge_graph_repository
        if not kg_repo:
            logger.error("Failed to get knowledge graph repository")
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to get knowledge graph repository"}
            )
        
        # Initialize or get existing graph
        logger.info("Initializing knowledge graph")
        graph_id = await kg_repo.initialize_graph(owner_id=request.user_id)
        if not graph_id:
            logger.error("Failed to initialize knowledge graph")
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to initialize knowledge graph"}
            )
        logger.info(f"Graph initialized with ID: {graph_id}")
        
        # Clear existing graph data
        logger.info("Clearing existing graph data")
        await kg_repo.clear_graph(graph_id)
        
        # Get documents to process
        logger.info("Fetching documents to process")
        if request.user_id:
            documents = await document_repo.find_accessible(request.user_id)
        else:
            documents = await document_repo.find({})
        logger.info(f"Found {len(documents)} documents to process")
        
        # Process documents to build the graph
        node_count = 0
        edge_count = 0
        
        for doc in documents:
            logger.info(f"Processing document: {doc.get('filename', 'Unknown')}")
            try:
                # Add document as a node
                doc_node_id = await kg_repo.add_node(
                    graph_id=graph_id,
                    label=doc.get('filename', 'Unknown'),
                    node_type="document",
                    properties={
                        "id": doc.get('id'),
                        "type": doc.get('metadata', {}).get('type', 'unknown')
                    }
                )
                
                if doc_node_id:
                    node_count += 1
                    logger.info(f"Added document node: {doc_node_id}")
                    
                    # Process document content
                    content = doc.get('content', '')
                    if not content:
                        logger.warning(f"No content found for document: {doc.get('filename', 'Unknown')}")
                        continue
                        
                    logger.info(f"Extracting keywords from document: {doc.get('filename', 'Unknown')}")
                    logger.debug(f"Document content length: {len(content)}")
                    
                    keywords = extract_sample_keywords(content)
                    logger.info(f"Extracted {len(keywords)} keywords: {keywords}")
                    
                    for keyword in keywords:
                        try:
                            # Add keyword as a node
                            keyword_node_id = await kg_repo.add_node(
                                graph_id=graph_id,
                                label=keyword,
                                node_type="keyword"
                            )
                            
                            if keyword_node_id:
                                node_count += 1
                                logger.info(f"Added keyword node: {keyword_node_id}")
                                
                                # Add relationship between document and keyword
                                edge_id = await kg_repo.add_edge(
                                    graph_id=graph_id,
                                    source_id=doc_node_id,
                                    target_id=keyword_node_id,
                                    relation="contains"
                                )
                                
                                if edge_id:
                                    edge_count += 1
                                    logger.info(f"Added edge: {edge_id}")
                        except Exception as e:
                            logger.error(f"Error processing keyword '{keyword}': {str(e)}")
                            continue
            except Exception as e:
                logger.error(f"Error processing document {doc.get('filename', 'Unknown')}: {str(e)}")
                continue
        
        # Get final graph stats
        logger.info("Getting final graph statistics")
        stats = await kg_repo.get_graph_stats(graph_id)
        
        logger.info(f"Knowledge graph built successfully with {stats.get('nodes', 0)} nodes and {stats.get('edges', 0)} edges")
        
        return {
            "message": "Knowledge graph built successfully",
            "graph_id": graph_id,
            "stats": stats
        }
    
    except (ValueError, AttributeError) as e:
        logger.error(f"Invalid graph data: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid graph data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error(f"Database operation error: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except Exception as e:
        logger.error(f"Unexpected error in build_knowledge_graph: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Unexpected error: {str(e)}"}
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