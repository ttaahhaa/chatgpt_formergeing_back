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

# Setup logging
from app.utils.logging_utils import setup_logging
logger = setup_logging()

# Import project modules
from app.core.document_loader import DocumentLoader
from app.core.vector_store import VectorStore
from app.core.llm import LLMChain
from app.core.hybrid_retrieval import HybridRetrieval

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
document_loader = DocumentLoader()
vector_store = VectorStore()
llm_chain = LLMChain()
retriever = HybridRetrieval(vector_store)

# Store components in app state
app.state.document_loader = document_loader
app.state.vector_store = vector_store
app.state.llm_chain = llm_chain
app.state.retriever = retriever

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
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        file_path = os.path.join(logs_dir, filename)
        
        if not os.path.exists(file_path):
            return JSONResponse(
                status_code=404,
                content={"error": f"Log file not found: {filename}"}
            )
        
        with open(file_path, "r") as f:
            content = f.read()
        
        return {"filename": filename, "content": content}
    except Exception as e:
        logger.error(f"Error retrieving log content: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving log content: {str(e)}"}
        )

# Run server
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)