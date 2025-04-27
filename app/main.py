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
    allow_origins=["*"],
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

# API routes
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Document QA Assistant API is running"}

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