# Python standard library imports
import json
import logging
import os
import tempfile
import traceback
import uuid
from contextlib import asynccontextmanager
from asyncio import wait_for, TimeoutError as AsyncTimeoutError
from datetime import datetime
from typing import Dict, List, Optional, Any
import platform
import sys
import urllib.parse

# Third-party imports
import uvicorn
import pymongo
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse as FastAPIStreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import psutil
import jwt
# Local imports
from app.core.document_loader import DocumentLoader
from app.core.hybrid_retrieval import HybridRetriever
from app.core.llm import LLMChain
from app.core.mongodb_logger import MongoDBLogHandler, test_mongodb_logger
from app.core.vector_store_hybrid import get_hybrid_vector_store
from app.database import initialize_database
from app.database import close_database_connections
from app.database.models import Conversation
from app.database.config import mongodb_config
from app.database.repositories.factory import repository_factory
from app.utils.jwt_utils import create_access_token, verify_token, Token, TokenData
from app.utils.logging_utils import setup_logging
from app.core.llm_streaming import StreamingLLMChain
from app.core.embeddings import Embeddings


# Setup logging
today = datetime.now().strftime("%Y%m%d")
base_dir = os.path.dirname(os.path.dirname(__file__))
logs_dir = os.path.join(base_dir, "logs")
os.makedirs(logs_dir, exist_ok=True)

log_file = os.path.join(logs_dir, f"app_mongodb_{today}.log")

# Setup standard file logger (INFO and above)
logger = setup_logging(log_file=log_file, log_level="INFO", app_name="app_mongodb")
logger.info("MongoDB API Service starting")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    try:
        logger.info("Initializing database connection")
        initialized = await initialize_database()
        if not initialized:
            logger.error("Failed to initialize database")
        else:
            logger.info("Database initialized successfully")
            
            # Setup MongoDB log handler AFTER database is initialized
            try:
                # Get log repository
                log_repo = repository_factory.log_repository
                
                # Remove any existing MongoDB handlers to avoid duplicates
                root_logger = logging.getLogger()
                for handler in root_logger.handlers[:]:
                    if isinstance(handler, MongoDBLogHandler):
                        logger.info("Removing existing MongoDB log handler")
                        root_logger.removeHandler(handler)
                
                # Create and configure a new MongoDB log handler
                mongo_handler = MongoDBLogHandler(level=logging.WARNING)
                mongo_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
                
                # Initialize repository directly
                mongo_handler.repository = log_repo
                mongo_handler.ready = True
                
                # Add to root logger
                root_logger.addHandler(mongo_handler)
                
                # Log test messages
                logger.warning("MongoDB logging test - WARNING level message")
                logger.error("MongoDB logging test - ERROR level message")
                logger.info("MongoDB logger initialization complete")
                
                # Run direct test for MongoDB logging
                logger.info("Running direct MongoDB logger test")
                test_result = test_mongodb_logger()
                if test_result:
                    logger.info("Direct MongoDB logger test successful")
                else:
                    logger.error("Direct MongoDB logger test failed")
                    
            except (ValueError, AttributeError) as e:
                logger.error("Error setting up MongoDB logger: %s", str(e))
                logger.error(traceback.format_exc())
    except (ConnectionError, RuntimeError) as e:
        logger.error("Error during startup: %s", str(e))
        logger.error(traceback.format_exc())

    yield  # This is where FastAPI runs and serves requests
    
    # Shutdown
    try:
        logger.info("Closing database connections")
        await close_database_connections()
        logger.info("Database connections closed")
    except (ConnectionError, RuntimeError) as e:
        logger.error("Error during shutdown: %s", str(e))
        logger.error(traceback.format_exc())

# Create FastAPI app with lifespan handler
app = FastAPI(
    title="Document QA Assistant API with MongoDB",
    lifespan=lifespan
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core components
logger.info("Initializing core components")
document_loader = DocumentLoader()
vector_store = get_hybrid_vector_store()
llm_chain = LLMChain()
retriever = HybridRetriever()
streaming_llm = StreamingLLMChain()

# Store components in app state
app.state.document_loader = document_loader
app.state.vector_store = vector_store
app.state.llm_chain = llm_chain
app.state.retriever = retriever
app.state.streaming_llm = streaming_llm
logger.info("Core components initialized successfully")

# Get repositories
app.state.document_repo = repository_factory.document_repository
app.state.embedding_repo = repository_factory.embedding_repository
app.state.conversation_repo = repository_factory.conversation_repository
app.state.user_repo = repository_factory.user_repository

# Create data models
class QueryRequest(BaseModel):
    """Request model for document queries.
    
    Attributes:
        query: The search query text
        conversation_id: Optional ID to link queries in a conversation
        user_id: Optional ID of the user making the query
    """
    query: str
    conversation_id: Optional[str] = None  
    user_id: Optional[str] = None

class QueryResponse(BaseModel):
    """Response model for document queries.
    
    Attributes:
        response: The answer text generated from relevant documents
        sources: Optional list of source documents used to generate the answer
        conversation_id: Optional ID linking to the original conversation
    """
    response: str
    sources: Optional[List[Dict[str, Any]]] = None
    conversation_id: Optional[str] = None

class ChatRequest(BaseModel):
    """Request model for chat messages.
    
    Attributes:
        message: The chat message text
        conversation_id: Optional ID to link messages in a conversation
        user_id: Optional ID of the user sending the message
        mode: Chat mode - auto (default), documents_only, or general_knowledge
    """
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    mode: Optional[str] = "auto"  # auto, documents_only, general_knowledge

class ChatResponse(BaseModel):
    """Response model for chat messages.
    
    Attributes:
        response: The generated chat response text
        sources: Optional list of source documents used in the response
        conversation_id: Optional ID linking to the conversation
    """
    response: str
    sources: Optional[List[Dict[str, Any]]] = None
    conversation_id: Optional[str] = None

class UserRequest(BaseModel):
    """Request model for user registration/creation.
    
    Attributes:
        username: User's chosen username
        email: User's email address
        password: User's password
    """
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    """Response model for user data.
    
    Attributes:
        id: Unique identifier for the user
        username: User's username
        email: User's email address
        role: User's role/permission level
    """
    id: str
    username: str
    email: str
    role: str

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/login")

# Authentication dependency
async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Get the current authenticated user from the JWT token."""
    try:
        token_data = verify_token(token)
        if not token_data or not token_data.user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials: missing user data"
            )
        return token_data
    except jwt.PyJWTError as exc:
        logger.error("Authentication error: Invalid token - %s", str(exc))
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        ) from exc
    except HTTPException as exc:
        # Re-raise HTTP exceptions from verify_token
        raise exc
    except Exception as exc:
        logger.error("Unexpected authentication error: %s", str(exc))
        raise HTTPException(
            status_code=500,
            detail="Internal server error during authentication"
        ) from exc

# Permission dependency
def check_permission(permission: str):
    """Check if the current user has the required permission.
    
    Args:
        permission (str): The permission to check for.
        
    Returns:
        A dependency function that checks the user's permission.
        
    Raises:
        HTTPException: If the user doesn't have the required permission.
    """
    async def _check_permission(current_user: TokenData = Depends(get_current_user)):
        try:
            has_permission = await app.state.user_repo.check_permission(current_user.user_id, permission)
            if not has_permission:
                raise HTTPException(
                    status_code=403,
                    detail="Not enough permissions"
                )
            return current_user
        except (ValueError, AttributeError) as e:
            logger.error("Permission check error: %s", str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Error checking permissions: {str(e)}"
            ) from e
    return _check_permission

# API routes
@app.get("/")
async def root():
    """Return a welcome message indicating the API is running."""
    logger.info("Root endpoint accessed")
    return {"message": "Document QA Assistant API with MongoDB is running"}

@app.get("/api/status")
async def get_status():
    """Get system status information.
    
    This endpoint collects and returns various system status metrics:
    1. Document count from MongoDB
    2. LLM (Language Model) availability status and current model
    3. Embedding model status
    4. MongoDB statistics (docs, embeddings, conversations)
    5. System information (OS, memory usage, Python version)
    
    Returns:
        JSON with status metrics or error response
    """
    try:
        logger.info("Retrieving system status")

        # Step 1: Get document count from MongoDB
        document_count = await app.state.document_repo.count({})

        # Step 2: Check LLM status
        llm_status = "unavailable"
        current_model = "unknown"
        try:
            ollama_status = app.state.llm_chain.check_ollama_status()
            if ollama_status.get("status") == "available":
                llm_status = "available"
                if ollama_status.get("models"):
                    current_model = ollama_status["models"][0]
        except (ConnectionError, RuntimeError) as e:
            logger.error("LLM status check failed: %s", str(e))

        # Step 3: Check embedding model status
        embedding_status = "unavailable"
        try:
            embedding_model = Embeddings()
            model_status = embedding_model.check_model_status()
            embedding_status = model_status.get("status", "unavailable")
        except (ConnectionError, RuntimeError) as e:
            logger.error("Embedding status check failed: %s", str(e))

        # Step 4: MongoDB stats
        mongo_stats = {
            "documents": document_count,
            "embeddings": await app.state.embedding_repo.count({}),
            "conversations": await app.state.conversation_repo.count({})
        }

        # Step 5: System info
        system_info = {
            "os": platform.system(),
            "architecture": platform.machine(), 
            "python_version": sys.version.split()[0],
            "app_version": "1.0.0"
        }

        memory_usage = f"{psutil.Process().memory_info().rss / (1024 * 1024):.2f} MB"

        # Final response
        status_data = {
            "llm_status": llm_status,
            "embeddings_status": embedding_status,
            "current_model": current_model,
            "document_count": document_count,
            "database_stats": mongo_stats,
            "memory_usage": memory_usage,
            "system_info": system_info
        }

        logger.info("Status retrieved successfully")
        return status_data

    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid data format: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Invalid data format: {str(e)}"}
        )

@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(check_permission("documents:upload"))
):
    """Upload a document to the system.
    
    Args:
        file (UploadFile): The file to upload.
        current_user (TokenData): The authenticated user.
        
    Returns:
        JSON response indicating success or failure.
        
    Raises:
        HTTPException: If there's an error processing the file.
    """
    try:
        logger.info("Uploading file: %s", file.filename)

        # Save uploaded file to a temp path using the original filename
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.filename)

        with open(temp_path, "wb") as f:
            contents = await file.read()
            f.write(contents)

        # Load document using your loader
        loaded = app.state.document_loader.load(temp_path)

        # Flatten the document dict for MongoDB
        document = {
            "id": f"doc_{uuid.uuid4()}",
            "filename": file.filename,
            "extension": loaded.get("extension") or os.path.splitext(file.filename)[1].lower(),
            "content": loaded.get("content", ""),
            "metadata": loaded.get("metadata", {}),
            "owner_id": current_user.user_id,  # Set document owner
            "created_at": datetime.utcnow()
        }
        
        # Add to MongoDB via vector store
        success = await app.state.vector_store.async_store.add_document(document)

        # Clean up temp file
        os.unlink(temp_path)

        if success:
            logger.info("Successfully uploaded %s", file.filename)
            return {"message": f"Successfully uploaded {file.filename}"}
        else:
            logger.error("Failed to add document to database: %s", file.filename)
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to add document to database"}
            )

    except ValueError as e:
        logger.error("Invalid document format: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid document format: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except OSError as e:
        logger.error("File operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"File operation error: {str(e)}"}
        )

@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Process a query against the document store."""
    try:
        logger.info("Processing query: %s", request.query)
        
        # Retrieve relevant documents
        results = await app.state.vector_store.async_store.query(request.query, top_k=5)
        
        if not results:
            logger.warning("No relevant documents found for query")
        
        # Generate response with sources
        llm_response = app.state.llm_chain.query_with_sources(
            request.query, 
            results
        )
        # Save to conversation if ID provided
        if request.conversation_id:
            # Add user message
            await app.state.conversation_repo.add_message(
                conversation_id=request.conversation_id,
                role="user",
                content=request.query
            )
            
            # Add assistant response
            await app.state.conversation_repo.add_message(
                conversation_id=request.conversation_id,
                role="assistant",
                content=llm_response["response"]
            )
        
        # Create response
        response = QueryResponse(
            response=llm_response["response"],
            sources=llm_response["sources"],
            conversation_id=request.conversation_id
        )
        
        logger.info("Query processed successfully")
        return JSONResponse(
            status_code=410,
            content={
                "warning": "This endpoint is deprecated. Please use /api/chat instead.",
                "data": response.dict()
            }
        )
    
    except (ValueError, AttributeError) as e:
        logger.error("Invalid query format: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid query format: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@app.post("/api/chat")
async def chat(
    request: dict,
    current_user: TokenData = Depends(check_permission("chat:send"))
):
    """Process a chat message and return a response."""
    try:
        # Extract message and conversation ID from request
        message = request.get("message", "")
        conversation_id = request.get("conversation_id")
        mode = request.get("mode", "auto")  # Get the mode parameter
        
        if not message:
            return JSONResponse(
                status_code=400,
                content={"error": "Message is required"}
            )
        
        # Get LLM instance
        llm = LLMChain()
        
        # Get conversation history if conversation_id is provided
        conversation_context = []
        if conversation_id:
            conversation_repo = repository_factory.conversation_repository
            conversation = await conversation_repo.find_by_id(conversation_id)
            
            if conversation:
                # Check ownership
                if conversation.owner_id != current_user.user_id:
                    return JSONResponse(
                        status_code=403,
                        content={"error": "You don't have permission to access this conversation"}
                    )
                    
                # Convert ConversationMessage objects to dictionaries if needed
                for msg in conversation.messages:
                    # Check if it's already a dict or needs conversion
                    if isinstance(msg, dict):
                        # Make sure the dict has the required fields
                        if "role" in msg and "content" in msg:
                            conversation_context.append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })
                    else:
                        # It's a Pydantic model, extract the fields
                        conversation_context.append({
                            "role": msg.role,
                            "content": msg.content
                        })
        
        # Determine if we should use documents based on the mode
        use_documents = mode == "documents_only" or mode == "auto"
        
        # Get response from LLM
        if use_documents:
            # Get relevant documents
            results = await app.state.vector_store.async_store.query(message, top_k=5)
            
            if not results:
                logger.warning("No relevant documents found for query")
            
            # Generate response with sources
            llm_response = app.state.llm_chain.query_with_sources(
                message, 
                results
            )
            response = llm_response["response"]
            sources = llm_response["sources"]
        else:
            # Generate general response
            response = llm.generate_response(message, conversation_context)
            sources = None
        
        # Save the conversation if conversation_id is provided
        if conversation_id:
            # Save user message
            user_message = {
                "role": "user",
                "content": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Save assistant response
            assistant_message = {
                "role": "assistant",
                "content": response,
                "timestamp": datetime.utcnow().isoformat(),
                "sources": sources if sources else None
            }
            
            # Add messages to conversation
            conversation_repo = repository_factory.conversation_repository
            conversation = await conversation_repo.find_by_id(conversation_id)
            
            if conversation:
                # Check ownership
                if conversation.owner_id != current_user.user_id:
                    return JSONResponse(
                        status_code=403,
                        content={"error": "You don't have permission to modify this conversation"}
                    )
                    
                # Get existing messages
                messages = conversation.messages
                
                # Add new messages
                messages.append(user_message)
                messages.append(assistant_message)
                
                # Update conversation
                await conversation_repo.update(conversation_id, {
                    "messages": messages,
                    "preview": message[:50] + "..." if len(message) > 50 else message,
                    "last_updated": datetime.utcnow()
                })
            else:
                # Create new conversation
                conversation_data = {
                    "id": conversation_id,
                    "owner_id": current_user.user_id,
                    "messages": [user_message, assistant_message],
                    "preview": message[:50] + "..." if len(message) > 50 else message,
                    "last_updated": datetime.utcnow()
                }
                
                # Use the Conversation model to create a new conversation
                conversation_obj = Conversation(**conversation_data)
                await conversation_repo.create(conversation_obj)
        
        # Return response
        return {
            "response": response,
            "sources": sources,
            "conversation_id": conversation_id
        }
    except (ValueError, AttributeError) as e:
        logger.error("Invalid request format: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid request format: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except (IOError, OSError) as e:
        logger.error("File operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"File operation error: {str(e)}"}
        )

@app.post("/api/clear_documents")
async def clear_documents():
    """Clear all documents from the system."""
    try:
        # Use the vector store's clear method
        success = await app.state.vector_store.async_store.clear()
        
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

@app.get("/api/documents")
async def get_documents(
    current_user: TokenData = Depends(check_permission("documents:view"))
):
    """Get all documents in the system."""
    try:
        # Get documents owned by or shared with this user
        documents = await app.state.document_repo.find_accessible(current_user.user_id)
        
        docs = []
        for doc in documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            docs.append(doc)
        
        return {"documents": docs}
    
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid data format: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Invalid data format: {str(e)}"}
        )

@app.post("/api/delete_document")
async def delete_document(
    document_id: str = Form(...),
    current_user: TokenData = Depends(check_permission("documents:delete"))
):
    """Delete a document from the system."""
    try:
        # Check if document exists
        document = await app.state.document_repo.find_by_id(document_id)
        
        if not document:
            return JSONResponse(
                status_code=404,
                content={"error": f"Document not found: {document_id}"}
            )
        
        # Check ownership if user_id provided
        owner_id = document["owner_id"] if isinstance(document, dict) else document.owner_id
        if owner_id and owner_id != current_user.user_id:
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to delete this document"}
            )
        
        # Delete embedding first
        await app.state.embedding_repo.delete_by_document_id(document_id)
        
        # Delete document
        success = await app.state.document_repo.delete(document_id)
        
        if success:
            logger.info("Deleted document: %s", document_id)
            return {"message": "Document deleted successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to delete document"}
            )
    
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid document ID: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid document ID: {str(e)}"}
        )

@app.post("/api/users/login", response_model=Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate a user and return JWT token."""
    try:
        # Authenticate user
        user = await app.state.user_repo.authenticate(form_data.username, form_data.password)
        
        if not user:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid username or password"}
            )
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user["username"], "user_id": user["id"]}
        )
        
        logger.info("User logged in: %s", user['username'])
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    
    except (ValueError, AttributeError) as e:
        logger.error("Error logging in: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Error logging in: {str(e)}"}
        )

@app.get("/api/users/me")
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """Get the current user's profile."""
    try:
        user = await app.state.user_repo.find_by_id(current_user.user_id)
        
        if not user:
            return JSONResponse(
                status_code=404,
                content={"error": "User not found"}
            )
        
        # Get user permissions
        permissions = await app.state.user_repo.get_user_permissions(user["id"])
        
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "permissions": permissions,
            "created_at": user["created_at"]
        }
    
    except (ValueError, AttributeError) as e:
        logger.error("Error retrieving user: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving user: {str(e)}"}
        )

@app.post("/api/users/change-password")
async def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    current_user: TokenData = Depends(get_current_user)
):
    """Change a user's password."""
    try:
        # Get user
        user = await app.state.user_repo.find_by_id(current_user.user_id)
        
        if not user:
            return JSONResponse(
                status_code=404,
                content={"error": "User not found"}
            )
        
        # Verify current password
        if not await app.state.user_repo.authenticate(user["username"], current_password):
            return JSONResponse(
                status_code=401,
                content={"error": "Current password is incorrect"}
            )
        
        # Update password
        success = await app.state.user_repo.update_password(user["id"], new_password)
        
        if not success:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to update password"}
            )
        
        logger.info("Password changed for user: %s", user['username'])
        return {"message": "Password changed successfully"}
    
    except (ValueError, AttributeError) as e:
        logger.error("Invalid password format: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid password format: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

# Conversations endpoints
@app.post("/api/conversations/new")
async def new_conversation(
    current_user: TokenData = Depends(check_permission("chat:create"))
):
    """Create a new conversation."""
    try:
        # Ensure we have a valid user_id
        if not current_user or not current_user.user_id:
            return JSONResponse(
                status_code=401,
                content={"error": "User not authenticated"}
            )

        conversation_repo = repository_factory.conversation_repository
        conversation_id = await conversation_repo.create_new_conversation(current_user.user_id)
        
        if not conversation_id:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to create new conversation"}
            )
        
        return {"conversation_id": conversation_id}
    except (ValueError, AttributeError) as e:
        logger.error("Invalid user data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid user data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@app.get("/api/conversations")
async def get_conversations(
    current_user: TokenData = Depends(get_current_user)
):
    """Returns a list of available conversations for the sidebar."""
    try:
        # Check if user has permission to view conversations
        has_permission = await app.state.user_repo.check_permission(current_user.user_id, "chat:view")
        if not has_permission:
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to view conversations"}
            )

        conversation_repo = repository_factory.conversation_repository
        conversations = await conversation_repo.get_conversation_list(current_user.user_id)
        return {"conversations": conversations}
    except (ValueError, AttributeError) as e:
        logger.error("Invalid user data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid user data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    
@app.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get a specific conversation with its messages."""
    try:
        logger.info("Retrieving conversation: %s", conversation_id)
        
        # Check if user has permission to view conversations
        has_permission = await app.state.user_repo.check_permission(current_user.user_id, "chat:view")
        if not has_permission:
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to view conversations"}
            )
        
        conversation_repo = repository_factory.conversation_repository
        
        # Get the conversation
        conversation = await conversation_repo.find_by_id(conversation_id)
        
        if not conversation:
            logger.warning("Conversation not found: %s", conversation_id)
            return JSONResponse(
                status_code=404,
                content={"error": f"Conversation not found: {conversation_id}"}
            )
            
        # Check ownership
        owner_id = conversation.get("owner_id") if isinstance(conversation, dict) else conversation.owner_id
        if owner_id != current_user.user_id:
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to view this conversation"}
            )
        
        # Return in the format expected by frontend
        return {
            "conversation_id": conversation["id"] if isinstance(conversation, dict) else conversation.id,
            "messages": conversation["messages"] if isinstance(conversation, dict) else conversation.messages,
            "preview": conversation["preview"] if isinstance(conversation, dict) else conversation.preview,
            "last_updated": conversation["last_updated"] if isinstance(conversation, dict) else conversation.last_updated
        }
    except (ValueError, AttributeError) as e:
        logger.error("Invalid conversation data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid conversation data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    
@app.post("/api/conversations/save")
async def save_conversation(
    data: dict,
    current_user: TokenData = Depends(get_current_user)
):
    """Save a conversation with proper field handling."""
    try:
        # Ensure we have a valid user_id
        if not current_user or not current_user.user_id:
            return JSONResponse(
                status_code=401,
                content={"error": "User not authenticated"}
            )

        conversation_repo = repository_factory.conversation_repository
        
        conv_id = data.get("conversation_id")
        if not conv_id:
            return JSONResponse(
                status_code=400,
                content={"error": "conversation_id is required"}
            )
        
        logger.info("Saving conversation: %s", conv_id)
        
        # Ensure all required fields exist
        if "messages" not in data and "history" in data:
            # Convert history to messages (frontend may use different field names)
            data["messages"] = data.pop("history")
        elif "messages" not in data:
            # Ensure messages exists
            data["messages"] = []
            
        # Ensure preview exists
        if not data.get("preview"):
            data["preview"] = "New Conversation"
            
        # Ensure last_updated exists
        if not data.get("last_updated"):
            data["last_updated"] = datetime.utcnow()
            
        # Check if conversation exists
        existing = await conversation_repo.find_by_id(conv_id)
        
        if existing:
            # Get owner_id safely whether it's a dict or model
            owner_id = existing.get("owner_id") if isinstance(existing, dict) else getattr(existing, "owner_id", None)
            
            # Check ownership
            if owner_id != current_user.user_id:
                return JSONResponse(
                    status_code=403,
                    content={"error": "You don't have permission to edit this conversation"}
                )
                
            # Update existing conversation
            update_data = {
                "messages": data.get("messages", []),
                "preview": data.get("preview", "Conversation"),
                "last_updated": data.get("last_updated", datetime.utcnow())
            }
            
            success = await conversation_repo.update(conv_id, update_data)
            if not success:
                return JSONResponse(
                    status_code=500,
                    content={"error": f"Failed to update conversation {conv_id}"}
                )
        else:
            # Create new conversation
            conversation_data = {
                "id": conv_id,
                "owner_id": current_user.user_id,
                "messages": data.get("messages", []),
                "preview": data.get("preview", "New Conversation"),
                "last_updated": data.get("last_updated", datetime.utcnow())
            }
            
            # Create new conversation using the repository
            result = await conversation_repo.create(conversation_data)
            if not result:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to create conversation"}
                )
        
        logger.info("Successfully saved conversation: %s", conv_id)
        return {"status": "saved"}
    except (ValueError, AttributeError) as e:
        logger.error("Invalid conversation data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid conversation data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@app.post("/api/conversations/clear")
async def clear_conversations(
    current_user: TokenData = Depends(check_permission("chat:delete"))
):
    """Clear all conversations."""
    try:
        logger.info("Clearing all conversations")
        
        conversation_repo = repository_factory.conversation_repository
        
        # Use the MongoDB collection directly for a bulk delete operation
        result = await conversation_repo.collection.delete_many({"owner_id": current_user.user_id})
        
        deleted_count = result.deleted_count
        logger.info("Deleted %d conversations", deleted_count)
        
        if deleted_count > 0:
            return {"message": f"Successfully cleared {deleted_count} conversations"}
        else:
            logger.warning("No conversations found to clear")
            return {"message": "No conversations found to clear"}
            
    except (ValueError, AttributeError) as e:
        logger.error("Invalid user data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid user data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: TokenData = Depends(check_permission("chat:delete"))
):
    """Delete a single conversation by ID."""
    try:
        logger.info("Deleting conversation: %s", conversation_id)
        
        conversation_repo = repository_factory.conversation_repository
        
        # Get the conversation first to check ownership
        conversation = await conversation_repo.find_by_id(conversation_id)
        
        if not conversation:
            logger.warning("Conversation not found: %s", conversation_id)
            return JSONResponse(
                status_code=404,
                content={"error": f"Conversation not found: {conversation_id}"}
            )
        
        # Check ownership
        owner_id = conversation.get("owner_id") if isinstance(conversation, dict) else conversation.owner_id
        if owner_id != current_user.user_id:
            logger.warning("User %s attempted to delete conversation %s owned by %s", 
                         current_user.user_id, conversation_id, owner_id)
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to delete this conversation"}
            )
        
        # Delete the conversation
        result = await conversation_repo.delete(conversation_id)
        
        if result:
            logger.info("Successfully deleted conversation: %s", conversation_id)
            return {"message": "Conversation deleted successfully"}
        else:
            logger.error("Failed to delete conversation: %s", conversation_id)
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to delete conversation"}
            )
            
    except (ValueError, AttributeError) as e:
        logger.error("Invalid conversation data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid conversation data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

# Document sharing endpoints
@app.post("/api/documents/share")
async def share_document(
    document_id: str = Form(...),
    share_with_user_id: str = Form(...),
    current_user: TokenData = Depends(lambda: check_permission("documents:share"))
):
    """Share a document with another user."""
    try:
        # Check if document exists
        document = await app.state.document_repo.find_by_id(document_id)
        
        if not document:
            return JSONResponse(
                status_code=404,
                content={"error": f"Document not found: {document_id}"}
            )
        
        # Check ownership
        if document.owner_id != current_user.user_id:
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to share this document"}
            )
        
        # Check if target user exists
        target_user = await app.state.user_repo.find_by_id(share_with_user_id)
        
        if not target_user:
            return JSONResponse(
                status_code=404,
                content={"error": f"User not found: {share_with_user_id}"}
            )
        
        # Share document
        success = await app.state.document_repo.share_document(document_id, share_with_user_id)
        
        if success:
            logger.info("Shared document %s with user %s", document_id, share_with_user_id)
            return {"message": "Document shared successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to share document"}
            )
    
    except (ValueError, AttributeError) as e:
        logger.error("Invalid document or user data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid document or user data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@app.post("/api/documents/unshare")
async def unshare_document(
    document_id: str = Form(...),
    user_id: str = Form(...),
    current_user: TokenData = Depends(lambda: check_permission("documents:share"))
):
    """Remove a user's access to a shared document."""
    try:
        # Check if document exists
        document = await app.state.document_repo.find_by_id(document_id)
        
        if not document:
            return JSONResponse(
                status_code=404,
                content={"error": f"Document not found: {document_id}"}
            )
        
        # Check ownership
        if document.owner_id != current_user.user_id:
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to modify sharing for this document"}
            )
        
        # Unshare document
        success = await app.state.document_repo.unshare_document(document_id, user_id)
        
        if success:
            logger.info("Removed sharing for document %s from user %s", document_id, user_id)
            return {"message": "Document sharing removed successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to remove document sharing"}
            )
    
    except (ValueError, AttributeError) as e:
        logger.error("Invalid document or user data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid document or user data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )


# Add endpoint to check Ollama status
@app.get("/api/check_ollama")
async def check_ollama():
    """Check Ollama LLM service status."""
    try:
        logger.info("Checking Ollama status")
        status = app.state.llm_chain.check_ollama_status()
        logger.info("Ollama status: %s", status)
        return status
    except (ConnectionError, RuntimeError) as e:
        logger.error("Ollama service error: %s", str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "error": f"Ollama service error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid Ollama response: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"status": "unavailable", "error": f"Invalid Ollama response: {str(e)}"}
        )

# Add endpoint to set LLM model
@app.post("/api/set_model")
async def set_model(
    request: dict,
    current_user: TokenData = Depends(check_permission("model:change"))
):
    """Set the user's preferred LLM model."""
    try:
        if "model" not in request:
            return JSONResponse(
                status_code=400,
                content={"error": "No model specified"}
            )
        
        model = request.get("model")
        
        # Get user settings repository
        settings_repo = repository_factory.user_settings_repository
        
        # Update or create user settings
        settings = await settings_repo.find_by_user_id(current_user.user_id)
        if settings:
            await settings_repo.update(current_user.user_id, {
                "preferred_model": model,
                "updated_at": datetime.utcnow()
            })
        else:
            await settings_repo.create({
                "user_id": current_user.user_id,
                "preferred_model": model
            })
        
        return {"message": f"Model updated to {model}"}
    except (ValueError, AttributeError) as e:
        logger.error("Invalid model data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid model data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Model service error: %s", str(e))
        return JSONResponse(
            status_code=503,
            content={"error": f"Model service error: {str(e)}"}
        )

# Add endpoint to get available models
@app.get("/api/models")
async def get_models(
    current_user: TokenData = Depends(check_permission("model:view"))
):
    """Get available LLM models and user's preferred model."""
    try:
        # Get available models from Ollama
        ollama_status = app.state.llm_chain.check_ollama_status()
        models = ollama_status.get("models", [])
        
        # Get user's preferred model
        settings_repo = repository_factory.user_settings_repository
        user_settings = await settings_repo.find_by_user_id(current_user.user_id)
        preferred_model = user_settings.get("preferred_model") if user_settings else "mistral:latest"
        
        return {
            "models": models,
            "current_model": preferred_model
        }
    except (ConnectionError, RuntimeError) as e:
        logger.error("Model service error: %s", str(e))
        return JSONResponse(
            status_code=503,
            content={"error": f"Model service error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid model data: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Invalid model data: {str(e)}"}
        )

@app.get("/api/user/preferred-model")
async def get_user_preferred_model(
    current_user: TokenData = Depends(get_current_user)
):
    """Get the current user's preferred model."""
    try:
        # Get user settings repository
        settings_repo = repository_factory.user_settings_repository
        
        # Get user's settings
        user_settings = await settings_repo.find_by_user_id(current_user.user_id)
        
        # Return preferred model or default
        preferred_model = user_settings.get("preferred_model") if user_settings else "mistral:latest"
        
        return {
            "preferred_model": preferred_model
        }
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=503,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid user data: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Invalid user data: {str(e)}"}
        )

# Add endpoint to clear cache
@app.post("/api/clear_cache")
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

# Add endpoint to manage knowledge graph
@app.post("/api/knowledge_graph/build")
async def build_knowledge_graph(user_id: Optional[str] = Form(None)):
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
            documents = await app.state.document_repo.find_accessible(user_id)
        else:
            documents = await app.state.document_repo.find({})
        
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

@app.get("/api/knowledge_graph/stats")
async def get_knowledge_graph_stats(user_id: Optional[str] = Form(None)):
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

# Add these fixed endpoints to your app/main_mongodb.py file

@app.get("/api/logs")
async def get_logs():
    """Get a list of all log files with timeout protection."""
    try:
        # Wrap the repository call with a timeout
        try:
            # Get log repository
            log_repo = repository_factory.log_repository
            
            # Attempt to get log files with a 5-second timeout
            logs = await wait_for(log_repo.get_log_files(), timeout=5.0)
            
            # If no logs found, return empty list
            if not logs:
                logger.warning("No log files found")
                return {"logs": []}
                
            # Add debug information
            logger.info("Found %d log files", len(logs))
            return {"logs": logs}
            
        except AsyncTimeoutError:
            logger.error("Timeout fetching log files")
            # Return a fallback response
            current_date = datetime.now().strftime("%Y%m%d")
            return {
                "logs": [{
                    "filename": f"mongodb_{current_date}.log",
                    "size": 1024,  # Placeholder size
                    "last_modified": int(datetime.now().timestamp())
                }]
            }
    except (ValueError, AttributeError) as e:
        logger.error("Invalid log data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid log data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@app.get("/api/logs/{filename}")
async def get_log_content(filename: str):
    """Get the content of a specific log file with fallback mechanism."""
    try:
        # Try to get the logs with a timeout
        try:
            log_repo = repository_factory.log_repository
            content = await wait_for(log_repo.get_log_content(filename), timeout=5.0)
            
            # Return the content
            return {
                "filename": filename,
                "content": content
            }
        except AsyncTimeoutError:
            logger.error("Timeout fetching log content for %s", filename)
            
            # Query MongoDB directly as a fallback
            try:
                # Use direct PyMongo access as a fallback
                import re
                import pymongo
                from datetime import datetime, timedelta
                import urllib.parse
                from app.database.config import mongodb_config
                
                # Extract date from filename
                date_match = re.search(r'mongodb_(\d{8})\.log', filename)
                if not date_match:
                    return {"content": f"Invalid filename format: {filename}"}
                
                date_str = date_match.group(1)
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                
                # Create datetime objects for start and end of day
                start_date = datetime(year, month, day)
                end_date = start_date + timedelta(days=1)
                
                # Set up direct MongoDB connection
                username = urllib.parse.quote_plus(mongodb_config.username)
                password = urllib.parse.quote_plus(mongodb_config.password)
                mongo_uri = (
                    f"mongodb://{username}:{password}@{mongodb_config.host}:{mongodb_config.port}/"
                    f"{mongodb_config.database_name}?authSource={mongodb_config.auth_source}"
                )
                
                client = pymongo.MongoClient(mongo_uri)
                db = client[mongodb_config.database_name]
                collection = db["logs"]
                
                # Query for logs on the specified day
                cursor = collection.find({
                    "timestamp": {
                        "$gte": start_date,
                        "$lt": end_date
                    }
                }).sort("timestamp", 1)
                
                # Format logs
                log_lines = []
                for doc in cursor:
                    try:
                        timestamp = doc.get("timestamp")
                        if isinstance(timestamp, datetime):
                            timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        
                        level = doc.get("level", "INFO")
                        source = doc.get("source", "unknown")
                        message = doc.get("message", "")
                        
                        log_line = f"{timestamp} - {level} - {source} - {message}"
                        log_lines.append(log_line)
                    except (ValueError, AttributeError) as format_error:
                        log_lines.append(f"Error formatting log: {str(format_error)}")
                
                content = "\n".join(log_lines) if log_lines else f"No logs found for {date_str}"
                
                # Close the MongoDB connection
                client.close()
                
                return {
                    "filename": filename,
                    "content": content
                }
                
            except (ConnectionError, RuntimeError) as direct_error:
                logger.error("Direct MongoDB access failed: %s", str(direct_error))
                return {
                    "filename": filename,
                    "content": f"Error retrieving logs: Repository timeout and direct access failed.\n{str(direct_error)}"
                }
                
    except (ValueError, AttributeError) as e:
        logger.error("Invalid log data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid log data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

# Add this debug endpoint to help troubleshoot
@app.get("/api/logs/debug/test")
async def test_log_endpoints():
    """Test endpoint that creates logs and directly retrieves them."""
    try:
        # Generate a few test logs
        logger.warning("Test warning log from debug endpoint")
        logger.error("Test error log from debug endpoint")
        
        # Get the current date
        current_date = datetime.now().strftime("%Y%m%d")
        filename = f"mongodb_{current_date}.log"
        
        # Try direct PyMongo access
        
        # Set up direct MongoDB connection
        username = urllib.parse.quote_plus(mongodb_config.username)
        password = urllib.parse.quote_plus(mongodb_config.password)
        mongo_uri = (
            f"mongodb://{username}:{password}@{mongodb_config.host}:{mongodb_config.port}/"
            f"{mongodb_config.database_name}?authSource={mongodb_config.auth_source}"
        )
        
        client = pymongo.MongoClient(mongo_uri)
        db = client[mongodb_config.database_name]
        collection = db["logs"]
        
        # Get log count
        log_count = collection.count_documents({})
        
        # Get a few sample logs
        sample_logs = list(collection.find().sort("timestamp", -1).limit(5))
        sample_log_data = []
        
        for log in sample_logs:
            sample_log_data.append({
                "level": log.get("level"),
                "message": log.get("message"),
                "timestamp": str(log.get("timestamp")),
                "source": log.get("source")
            })
        
        # Close the MongoDB connection
        client.close()
        
        return {
            "status": "success",
            "log_count": log_count,
            "sample_logs": sample_log_data,
            "today_filename": filename
        }
        
    except (ConnectionError, RuntimeError) as e:
        logger.error("Debug endpoint error: %s", str(e))
        return {"error": f"Debug endpoint error: {str(e)}"}
    
@app.post("/api/rebuild_index")
async def rebuild_faiss_index():
    """Rebuild the FAISS index used for vector similarity search."""
    try:
        # Get async store from sync wrapper
        async_store = app.state.vector_store.async_store
        
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

@app.post("/api/chat/stream")
async def streaming_chat(
    request: dict,
    current_user: TokenData = Depends(lambda: check_permission("chat:stream"))
):
    """Stream chat responses token by token."""
    try:
        # Extract message and conversation ID from request
        message = request.get("message", "")
        conversation_id = request.get("conversation_id")
        mode = request.get("mode", "auto")
        
        if not message:
            return JSONResponse(
                status_code=400,
                content={"error": "Message is required"}
            )
        
        logger.info("Starting streaming chat for message: %s...", message[:50])
        
        # Get conversation context if ID provided
        conversation_context = []
        if conversation_id:
            conversation_repo = repository_factory.conversation_repository
            conversation = await conversation_repo.find_by_id(conversation_id)
            
            if conversation:
                # Use correct way to access messages
                messages = conversation["messages"] if isinstance(conversation, dict) else conversation.messages
                for msg in messages:
                    if isinstance(msg, dict):
                        if "role" in msg and "content" in msg:
                            conversation_context.append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })
                    else:
                        conversation_context.append({
                            "role": msg.role,
                            "content": msg.content
                        })
        
        # Determine if we should use documents
        sources = []
        use_documents = mode == "documents_only" or mode == "auto"
        
        if use_documents:
            # Use existing vector store from app state
            relevant_docs = await app.state.vector_store.async_store.query(message, top_k=5)
            
            # Format sources
            sources = [{
                "document": doc.get("filename", "Unknown"),
                "content": doc.get("content", ""),
                "relevance": doc.get("score", 0.0),
                "page": doc.get("metadata", {}).get("page", 1)
            } for doc in relevant_docs]
        
        # Create token generator
        async def token_generator():
            """Generate tokens from LLM and save conversation."""
            response_text = ""
            try:
                # Stream the response
                async for token_data in app.state.streaming_llm.stream_chat(
                    message=message,
                    conversation_context=conversation_context,
                    sources=sources
                ):
                    if "token" in token_data:
                        response_text += token_data["token"]
                        yield f"data: {json.dumps({'token': token_data['token']})}\n\n"
                    elif "error" in token_data:
                        yield f"data: {json.dumps({'error': token_data['error']})}\n\n"
                        return
                    elif token_data.get("done", False):
                        # Send completion with sources
                        yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"
                        
                        # Save conversation after completion
                        if conversation_id:
                            await save_streaming_conversation(
                                conversation_id=conversation_id,
                                user_message=message,
                                assistant_response=response_text,
                                current_user=current_user,
                                sources=sources
                            )
                        
                        return
                
                # Send final event
                yield "data: [DONE]\n\n"
                
            except (ConnectionError, RuntimeError) as e:
                logger.error("Streaming error: %s", str(e))
                yield f"data: {json.dumps({'error': f'Streaming error: {str(e)}'})}\n\n"
                yield "data: [DONE]\n\n"
        
        # Return streaming response
        return FastAPIStreamingResponse(
            token_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable Nginx buffering
            }
        )
    
    except (ValueError, AttributeError) as e:
        logger.error("Invalid request format: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid request format: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except (IOError, OSError) as e:
        logger.error("Streaming error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Streaming error: {str(e)}"}
        )

async def save_streaming_conversation(
    conversation_id: str,
    user_message: str,
    assistant_response: str,
    current_user: TokenData,
    sources: list = None
) -> None:
    """Save streaming conversation after completion."""
    try:
        conversation_repo = repository_factory.conversation_repository
        
        # Get existing conversation or create new
        conversation = await conversation_repo.find_by_id(conversation_id)
        
        # Prepare messages
        user_msg = {
            "role": "user",
            "content": user_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        assistant_msg = {
            "role": "assistant",
            "content": assistant_response,
            "timestamp": datetime.utcnow().isoformat(),
            "sources": sources if sources else None
        }
        
        if conversation:
            # Update existing conversation
            # Create a new list with existing messages plus new ones
            existing_messages = conversation.messages if hasattr(conversation, 'messages') else []
            if isinstance(conversation, dict):
                existing_messages = conversation.get('messages', [])
            
            # Create new list with all messages
            messages = list(existing_messages)  # Create a new list
            messages.append(user_msg)
            messages.append(assistant_msg)
            
            await conversation_repo.update(conversation_id, {
                "messages": messages,
                "preview": user_message[:50] + "..." if len(user_message) > 50 else user_message,
                "last_updated": datetime.utcnow()
            })
        else:
            # Create new conversation
            conversation_data = {
                "id": conversation_id,
                "owner_id": current_user.user_id,
                "messages": [user_msg, assistant_msg],
                "preview": user_message[:50] + "..." if len(user_message) > 50 else user_message,
                "last_updated": datetime.utcnow()
            }
            
            # Use the Conversation model to create a new conversation
            conversation_obj = Conversation(**conversation_data)
            await conversation_repo.create(conversation_obj)
        
        logger.info("Saved streaming conversation: %s", conversation_id)
        
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
    except (ValueError, AttributeError) as e:
        logger.error("Invalid conversation data: %s", str(e))
    except (IOError, OSError) as e:
        logger.error("File operation error: %s", str(e))
    
# Run server
if __name__ == "__main__":
    logger.info("Starting FastAPI server with MongoDB support")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)