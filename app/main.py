import os
import logging
import tempfile
from typing import Dict, List, Optional, Any
from pathlib import Path
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime

# Setup logging with explicit date handling
from app.utils.logging_utils import setup_logging

# Get the current date for log file naming
today = datetime.now().strftime("%Y%m%d")
base_dir = os.path.dirname(os.path.dirname(__file__))
logs_dir = os.path.join(base_dir, "logs")
os.makedirs(logs_dir, exist_ok=True)

# Create log file path with today's date
log_file = os.path.join(logs_dir, f"app_{today}.log")

# Initialize logger with app name
logger = setup_logging(log_file=log_file, log_level="INFO", app_name="app")
logger.info("API Service starting")

# Import project modules
from app.core.document_loader import DocumentLoader
from app.core.vector_store import VectorStore
from app.core.llm import LLMChain
from app.core.hybrid_retrieval import HybridRetriever

# Create FastAPI app
app = FastAPI(title="Document QA Assistant API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change to specific origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core components
logger.info("Initializing core components")
document_loader = DocumentLoader()
vector_store = VectorStore()
llm_chain = LLMChain()
retriever = HybridRetriever()

# Store components in app state
app.state.document_loader = document_loader
app.state.vector_store = vector_store
app.state.llm_chain = llm_chain
app.state.retriever = retriever
logger.info("Core components initialized successfully")

# Create data models
class QueryRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    conversation_context: Optional[List[Dict[str, str]]] = None

class QueryResponse(BaseModel):
    response: str
    sources: Optional[List[Dict[str, Any]]] = None
    conversation_id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    conversation_context: Optional[List[Dict[str, str]]] = None
    mode: Optional[str] = "auto"  # auto, documents_only, general_knowledge

class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[Dict[str, Any]]] = None
    conversation_id: Optional[str] = None

# API routes
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Document QA Assistant API is running"}

# app/main.py
@app.get("/api/status")
async def get_status():
    """Get system status information."""
    try:
        # Get LLM status
        llm_status = app.state.llm_chain.check_ollama_status()
        
        # Get embeddings status
        embeddings_status = app.state.embeddings.check_model_status()
        
        # Get document count
        documents = app.state.vector_store.get_documents()
        
        # Get system info
        import platform
        import sys
        system_info = {
            "os": platform.system() + " " + platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "app_version": "1.0.0"
        }
        
        # Get memory usage
        import psutil
        memory_usage = "Normal"
        if psutil.virtual_memory().percent > 80:
            memory_usage = "High"
        
        return {
            "llm_status": llm_status.get("status", "unavailable"),
            "embeddings_status": embeddings_status.get("status", "unavailable"),
            "document_count": len(documents),
            "current_model": app.state.llm_chain.model_name,
            "memory_usage": memory_usage,
            "system_info": system_info
        }
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting system status: {str(e)}"}
        )

# app/main.py
@app.get("/api/models")
async def get_models():
    """Get available LLM models."""
    try:
        # Get available models from Ollama
        ollama_status = app.state.llm_chain.check_ollama_status()
        models = ollama_status.get("models", [])
        current_model = app.state.llm_chain.model_name
        
        return {
            "models": models,
            "current_model": current_model
        }
    except Exception as e:
        logger.error(f"Error getting models: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting models: {str(e)}"}
        )
        
@app.get("/api/status")
async def get_status():
    """Get system status information."""
    try:
        logger.info("Retrieving system status")
        
        # Get document count
        documents = app.state.vector_store.get_documents()
        document_count = len(documents)
        
        # Check LLM status
        llm_status = "available"
        current_model = "mistral:latest"  # Default model
        
        try:
            # Try to check Ollama status
            ollama_status = app.state.llm_chain.check_ollama_status()
            if ollama_status["status"] == "available":
                llm_status = "available"
                if ollama_status.get("models") and len(ollama_status["models"]) > 0:
                    current_model = ollama_status["models"][0]  # First model in the list
            else:
                llm_status = "unavailable"
        except Exception as e:
            logger.error(f"Error checking LLM status: {str(e)}")
            llm_status = "unavailable"
        
        # Check embedding status
        embedding_status = "unavailable"
        try:
            # Check if embedding model is available
            from app.core.embeddings import Embeddings
            embedding_model = Embeddings()
            model_status = embedding_model.check_model_status()
            if model_status["status"] == "available":
                embedding_status = "available"
            else:
                embedding_status = "unavailable"
        except Exception as e:
            logger.error(f"Error checking embedding status: {str(e)}")
            embedding_status = "unavailable"
        
        # Get vector store statistics
        vector_store_info = {
            "documents": document_count,
            "embeddings": len(app.state.vector_store.document_embeddings)
        }
        
        # Get system info
        import platform
        import sys
        system_info = {
            "os": platform.system(),
            "architecture": platform.machine(),
            "python_version": sys.version.split()[0],
            "app_version": "1.0.0"  # You could import this from __init__.py
        }
        
        # Estimate memory usage
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_usage = f"{memory_info.rss / (1024 * 1024):.2f} MB"
        
        status_data = {
            "llm_status": llm_status,
            "embeddings_status": embedding_status,
            "current_model": current_model,
            "document_count": document_count,
            "vector_store_info": vector_store_info,
            "memory_usage": memory_usage,
            "system_info": system_info
        }
        
        logger.info("Status retrieved successfully")
        return status_data
    except Exception as e:
        logger.error(f"Error retrieving status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving status: {str(e)}"}
        )

@app.get("/api/check_ollama")
async def check_ollama():
    """Check Ollama LLM service status."""
    try:
        logger.info("Checking Ollama status")
        status = app.state.llm_chain.check_ollama_status()
        logger.info(f"Ollama status: {status}")
        return status
    except Exception as e:
        logger.error(f"Error checking Ollama: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "unavailable", "error": f"Error checking Ollama: {str(e)}"}
        )
# app/main.py
@app.post("/api/set_model")
async def set_model(request: dict):
    """Set the current LLM model."""
    try:
        if "model" not in request:
            return JSONResponse(
                status_code=400,
                content={"error": "No model specified"}
            )
        
        model = request.get("model")
        app.state.llm_chain.model_name = model
        
        return {"message": f"Model updated to {model}"}
    except Exception as e:
        logger.error(f"Error setting model: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error setting model: {str(e)}"}
        )

# app/main.py
@app.post("/api/clear_cache")
async def clear_cache():
    """Clear application cache."""
    try:
        from app.utils.cache_utils import clear_cache
        result = clear_cache()
        
        if result:
            return {"message": "Cache cleared successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to clear cache"}
            )
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error clearing cache: {str(e)}"}
        )
    
    
# Add endpoint for chat functionality
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        logger.info(f"Processing chat message: {request.message}")
        
        # Check if we need document retrieval
        use_documents = request.mode != "general_knowledge"
        
        # Get conversation history
        conversation_context = request.conversation_context or []
        
        if use_documents:
            # Retrieve relevant documents
            documents = app.state.retriever.retrieve(request.message, top_k=5)
            
            # Generate response with sources
            result = app.state.llm_chain.query_with_sources(
                request.message, 
                documents
            )
            
            response = ChatResponse(
                response=result["response"],
                sources=result["sources"],
                conversation_id=request.conversation_id
            )
        else:
            # Generate response without document retrieval
            response_text = app.state.llm_chain.generate_response(
                request.message, 
                conversation_context
            )
            
            response = ChatResponse(
                response=response_text,
                sources=[],
                conversation_id=request.conversation_id
            )
        
        logger.info("Chat processed successfully")
        return response
    
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error processing chat: {str(e)}"}
        )
    
@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        logger.info(f"Uploading file: {file.filename}")
        
        # Save file to temp location
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        contents = await file.read()
        temp_file.write(contents)
        temp_file.close()
        
        # Load document
        document = app.state.document_loader.load(temp_file.name)
        
        # Check for errors
        if "error" in document:
            logger.error(f"Error loading document: {document['error']}")
            os.unlink(temp_file.name)
            return JSONResponse(
                status_code=400,
                content={"error": document["error"]}
            )
        
        # Add to vector store
        app.state.vector_store.add_document(document)
        app.state.vector_store.save()
        
        # Clean up temp file
        os.unlink(temp_file.name)
        
        logger.info(f"Successfully uploaded {file.filename}")
        return {"message": f"Successfully uploaded {file.filename}"}
    
    except Exception as e:
        logger.error(f"Error processing document {file.filename}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error processing document: {str(e)}"}
        )

@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    try:
        logger.info(f"Processing query: {request.query}")
        
        # Retrieve relevant documents
        documents = app.state.retriever.retrieve(request.query, top_k=5)
        
        # Generate response with sources
        result = app.state.llm_chain.query_with_sources(
            request.query, 
            documents
        )
        
        # Create response
        response = QueryResponse(
            response=result["response"],
            sources=result["sources"],
            conversation_id=request.conversation_id
        )
        
        logger.info("Query processed successfully")
        return response
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error processing query: {str(e)}"}
        )

@app.post("/api/clear_documents")
async def clear_documents():
    try:
        logger.info("Clearing all documents")
        app.state.vector_store.clear()
        return {"message": "Successfully cleared all documents"}
    except Exception as e:
        logger.error(f"Error clearing documents: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error clearing documents: {str(e)}"}
        )

@app.get("/api/documents")
async def get_documents():
    try:
        logger.info("Retrieving document list")
        documents = app.state.vector_store.get_documents()
        return {"documents": [doc.get("filename", "Unknown") for doc in documents]}
    except Exception as e:
        logger.error(f"Error retrieving documents: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving documents: {str(e)}"}
        )

# Create a route to access logs
@app.get("/api/logs")
async def get_logs():
    try:
        logger.info("Retrieving logs list")
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        log_files = []
        
        for filename in os.listdir(logs_dir):
            if filename.endswith('.log'):
                file_path = os.path.join(logs_dir, filename)
                file_size = os.path.getsize(file_path)
                mod_time = os.path.getmtime(file_path)
                
                log_files.append({
                    "filename": filename,
                    "size": file_size,
                    "last_modified": mod_time
                })
        
        logger.info(f"Found {len(log_files)} log files")
        return {"logs": log_files}
    except Exception as e:
        logger.error(f"Error retrieving logs: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving logs: {str(e)}"}
        )

@app.get("/api/logs/{filename}")
async def get_log_content(filename: str):
    try:
        logger.info(f"Retrieving content for log file: {filename}")
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        file_path = os.path.join(logs_dir, filename)
        
        if not os.path.exists(file_path):
            logger.warning(f"Log file not found: {filename}")
            return JSONResponse(
                status_code=404,
                content={"error": f"Log file not found: {filename}"}
            )
        
        with open(file_path, "r") as f:
            content = f.read()
        
        logger.info(f"Successfully retrieved content for log file: {filename}")
        return {"filename": filename, "content": content}
    except Exception as e:
        logger.error(f"Error retrieving log content: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving log content: {str(e)}"}
        )

# Run server
if __name__ == "__main__":
    logger.info("Starting FastAPI server")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)