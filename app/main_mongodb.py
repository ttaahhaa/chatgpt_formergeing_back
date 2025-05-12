import os
import logging
import tempfile
from typing import Dict, List, Optional, Any
from pathlib import Path
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse as FastAPIStreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
from contextlib import asynccontextmanager
import uuid
import json
import asyncio
import traceback

# Setup logging
from app.utils.logging_utils import setup_logging
from app.core.vector_store_hybrid import get_hybrid_vector_store
from app.core.mongodb_logger import MongoDBLogHandler, test_mongodb_logger
from app.core.llm_streaming import StreamingLLMChain, StreamingResponse

# Set up logging directories and filenames
today = datetime.now().strftime("%Y%m%d")
base_dir = os.path.dirname(os.path.dirname(__file__))
logs_dir = os.path.join(base_dir, "logs")
os.makedirs(logs_dir, exist_ok=True)

log_file = os.path.join(logs_dir, f"app_mongodb_{today}.log")

# Setup standard file logger (INFO and above)
logger = setup_logging(log_file=log_file, log_level="INFO", app_name="app_mongodb")
logger.info("MongoDB API Service starting")

# Import MongoDB and core components
from app.database import initialize_database
from app.database.repositories.factory import repository_factory
from app.core.vector_store_mongodb import get_vector_store
from app.core.document_loader import DocumentLoader
from app.core.llm import LLMChain
from app.core.hybrid_retrieval import HybridRetriever
from app.prompts import CODE_PROMPTS, GENERAL_PROMPTS, DOCUMENT_PROMPTS

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
                    
            except Exception as e:
                logger.error(f"Error setting up MongoDB logger: {str(e)}")
                logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        logger.error(traceback.format_exc())

    yield  # This is where FastAPI runs and serves requests
    
    # Shutdown
    try:
        logger.info("Closing database connections")
        from app.database import close_database_connections
        await close_database_connections()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        logger.error(traceback.format_exc())

# Create FastAPI app with lifespan handler
app = FastAPI(
    title="Document QA Assistant API with MongoDB",
    lifespan=lifespan
)

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

# Database dependency
async def get_db():
    """Database dependency injection."""
    initialized = await initialize_database()
    if not initialized:
        raise HTTPException(status_code=500, detail="Database connection failed")
    return True

# API routes
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Document QA Assistant API with MongoDB is running"}

@app.get("/api/status", dependencies=[Depends(get_db)])
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
        except Exception as e:
            logger.error(f"LLM status check failed: {str(e)}")

        # Step 3: Check embedding model status
        embedding_status = "unavailable"
        try:
            from app.core.embeddings import Embeddings
            embedding_model = Embeddings()
            model_status = embedding_model.check_model_status()
            embedding_status = model_status.get("status", "unavailable")
        except Exception as e:
            logger.error(f"Embedding status check failed: {str(e)}")

        # Step 4: MongoDB stats
        mongo_stats = {
            "documents": document_count,
            "embeddings": await app.state.embedding_repo.count({}),
            "conversations": await app.state.conversation_repo.count({})
        }

        # Step 5: System info
        import platform
        import sys
        import psutil

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

    except Exception as e:
        logger.error(f"Error retrieving status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving status: {str(e)}"}
        )

@app.post("/api/upload", dependencies=[Depends(get_db)])
async def upload_document(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None)
):
    """Upload a document to the system.
    
    This endpoint handles document uploads by:
    1. Saving the uploaded file to a temporary location
    2. Loading and processing the document using DocumentLoader
    3. Adding metadata like filename, owner ID, and unique document ID
    4. Storing the document in MongoDB via VectorStore
    5. Cleaning up temporary files
    
    Args:
        file: The uploaded file
        user_id: Optional user ID to associate with the document
        
    Returns:
        Success message or error details
    """
    try:
        logger.info(f"Uploading file: {file.filename}")

        # Save uploaded file to a temp path using the original filename
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.filename)

        with open(temp_path, "wb") as f:
            contents = await file.read()
            f.write(contents)

        # Load document using your loader
        document = app.state.document_loader.load(temp_path)
        
        # Check for errors from loader
        if "error" in document:
            logger.error(f"Error loading document: {document['error']}")
            os.unlink(temp_path)
            return JSONResponse(
                status_code=400,
                content={"error": document["error"]}
            )

        # Prepare document for MongoDB
        document["filename"] = file.filename
        
        # Add owner if provided
        if user_id:
            document["owner_id"] = user_id
        
        # Generate a unique ID
        document["id"] = f"doc_{uuid.uuid4()}"
        
        # Add to MongoDB via vector store
        success = await app.state.vector_store.async_store.add_document(document)

        # Clean up temp file
        os.unlink(temp_path)

        if success:
            logger.info(f"Successfully uploaded {file.filename}")
            return {"message": f"Successfully uploaded {file.filename}"}
        else:
            logger.error(f"Failed to add document to database: {file.filename}")
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to add document to database"}
            )

    except Exception as e:
        logger.error(f"Error processing document {file.filename}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error processing document: {str(e)}"}
        )


@app.post("/api/query", response_model=QueryResponse, dependencies=[Depends(get_db)])
async def query(request: QueryRequest):
    """
    DEPRECATED: This endpoint is deprecated and will be removed in a future version.
    Please use /api/chat endpoint instead with mode="documents_only" for similar functionality.
    """
    logger.warning("The /api/query endpoint is deprecated. Please use /api/chat instead.")
    
    try:
        logger.info(f"Processing query: {request.query}")
        
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
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error processing query: {str(e)}"}
        )


@app.post("/api/chat")
async def chat(request: dict):
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
        
        if use_documents:
            # Retrieve relevant documents using the vector store
            relevant_docs = await app.state.vector_store.async_store.query(message, top_k=5)
            
            # Get appropriate prompt based on document types
            has_code = any(doc.get("filename", "").endswith(('.py', '.js', '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.go', '.rs', '.ts')) for doc in relevant_docs)
            has_api = any("api" in doc.get("filename", "").lower() for doc in relevant_docs)
            has_system = any("system" in doc.get("filename", "").lower() for doc in relevant_docs)
            
            if has_code:
                system_prompt = DOCUMENT_PROMPTS["code_documentation"]
            elif has_api:
                system_prompt = DOCUMENT_PROMPTS["api_documentation"]
            elif has_system:
                system_prompt = DOCUMENT_PROMPTS["system_documentation"]
            else:
                system_prompt = DOCUMENT_PROMPTS["system"]
            
            # Generate response with document context
            response_with_sources = llm.query_with_sources(message, relevant_docs, system_prompt)
            response = response_with_sources["response"]
            sources = response_with_sources["sources"]
        else:
            # Check if it's a code-related question
            code_extensions = {'.py', '.js', '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.go', '.rs', '.ts'}
            error_keywords = {'error', 'exception', 'fail', 'crash', 'bug', 'issue'}
            how_to_keywords = {'how to', 'how do i', 'how can i', 'tutorial', 'guide'}
            
            is_code = any(ext in message.lower() for ext in code_extensions)
            has_error = any(keyword in message.lower() for keyword in error_keywords)
            is_how_to = any(keyword in message.lower() for keyword in how_to_keywords)
            
            if is_code:
                if has_error:
                    system_prompt = f"{CODE_PROMPTS['system']}\n\n{CODE_PROMPTS['error_handling']}"
                elif is_how_to:
                    system_prompt = f"{CODE_PROMPTS['system']}\n\n{CODE_PROMPTS['optimization']}"
                else:
                    system_prompt = CODE_PROMPTS['system']
            else:
                system_prompt = GENERAL_PROMPTS['system']
            
            # Just use the LLM without document context
            response = llm.generate_response(message, conversation_context, system_prompt)
            sources = []
        
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
                new_conversation = {
                    "id": conversation_id,
                    "messages": [user_message, assistant_message],
                    "preview": message[:50] + "..." if len(message) > 50 else message,
                    "last_updated": datetime.utcnow()
                }
                
                # Use the Conversation model to create a new conversation
                from app.database.models import Conversation
                conversation_obj = Conversation(**new_conversation)
                await conversation_repo.create(conversation_obj)
        
        # Return response
        return {
            "response": response,
            "sources": sources,
            "conversation_id": conversation_id
        }
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Chat processing error: {str(e)}"}
        )
    
@app.post("/api/clear_documents", dependencies=[Depends(get_db)])
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
    
    except Exception as e:
        logger.error(f"Error clearing documents: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error clearing documents: {str(e)}"}
        )

@app.get("/api/documents", dependencies=[Depends(get_db)])
async def get_documents(user_id: Optional[str] = None):
    """Get all documents in the system."""
    try:
        if user_id:
            # Get documents owned by or shared with this user
            documents = await app.state.document_repo.find_accessible(user_id)
        else:
            # Get all documents
            documents = await app.state.document_repo.find({})
        
        # Convert to dictionary format
        docs = [doc.dict() for doc in documents]
        
        return {"documents": docs}
    
    except Exception as e:
        logger.error(f"Error retrieving documents: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving documents: {str(e)}"}
        )

@app.post("/api/delete_document", dependencies=[Depends(get_db)])
async def delete_document(document_id: str = Form(...), user_id: Optional[str] = Form(None)):
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
        if user_id and document.owner_id and document.owner_id != user_id:
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to delete this document"}
            )
        
        # Delete embedding first
        await app.state.embedding_repo.delete_by_document_id(document_id)
        
        # Delete document
        success = await app.state.document_repo.delete(document_id)
        
        if success:
            logger.info(f"Deleted document: {document_id}")
            return {"message": f"Document deleted successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to delete document"}
            )
    
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error deleting document: {str(e)}"}
        )

# User management endpoints
@app.post("/api/users/register", response_model=UserResponse, dependencies=[Depends(get_db)])
async def register_user(request: UserRequest):
    """Register a new user."""
    try:
        # Check if username or email already exists
        existing_user = await app.state.user_repo.find_by_username(request.username)
        if existing_user:
            return JSONResponse(
                status_code=400,
                content={"error": "Username already exists"}
            )
        
        existing_email = await app.state.user_repo.find_by_email(request.email)
        if existing_email:
            return JSONResponse(
                status_code=400,
                content={"error": "Email already exists"}
            )
        
        # Create new user
        user_id = await app.state.user_repo.create_user(
            username=request.username,
            email=request.email,
            password=request.password,
            role="user"  # Default role
        )
        
        if not user_id:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to create user"}
            )
        
        # Get the created user
        user = await app.state.user_repo.find_by_id(user_id)
        if not user:
            return JSONResponse(
                status_code=500,
                content={"error": "User created but could not be retrieved"}
            )
        
        logger.info(f"Registered new user: {user.username}")
        
        # Return user data (excluding password)
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role
        )
    
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error registering user: {str(e)}"}
        )

@app.post("/api/users/login", dependencies=[Depends(get_db)])
async def login_user(username: str = Form(...), password: str = Form(...)):
    """Authenticate a user and return token."""
    try:
        # Authenticate user
        user = await app.state.user_repo.authenticate(username, password)
        
        if not user:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid username or password"}
            )
        
        # Generate a simple token (in a real app, use proper JWT)
        token = f"user_{user.id}_{uuid.uuid4()}"
        
        logger.info(f"User logged in: {user.username}")
        
        return {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }
    
    except Exception as e:
        logger.error(f"Error logging in: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error logging in: {str(e)}"}
        )

@app.get("/api/users/me", dependencies=[Depends(get_db)])
async def get_current_user(user_id: str = Form(...)):
    """Get the current user's profile."""
    try:
        user = await app.state.user_repo.find_by_id(user_id)
        
        if not user:
            return JSONResponse(
                status_code=404,
                content={"error": "User not found"}
            )
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at
        }
    
    except Exception as e:
        logger.error(f"Error retrieving user: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving user: {str(e)}"}
        )

@app.post("/api/users/change-password", dependencies=[Depends(get_db)])
async def change_password(
    user_id: str = Form(...),
    current_password: str = Form(...),
    new_password: str = Form(...)
):
    """Change a user's password."""
    try:
        # Verify current password
        user = await app.state.user_repo.find_by_id(user_id)
        
        if not user:
            return JSONResponse(
                status_code=404,
                content={"error": "User not found"}
            )
        
        # Authenticate with current password
        auth_user = await app.state.user_repo.authenticate(user.username, current_password)
        
        if not auth_user:
            return JSONResponse(
                status_code=401,
                content={"error": "Current password is incorrect"}
            )
        
        # Update to new password
        success = await app.state.user_repo.update_password(user_id, new_password)
        
        if not success:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to update password"}
            )
        
        logger.info(f"Password changed for user: {user.username}")
        return {"message": "Password changed successfully"}
    
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error changing password: {str(e)}"}
        )

# Conversations endpoints
@app.post("/api/conversations/new")
async def new_conversation():
    """Create a new conversation."""
    try:
        conversation_repo = repository_factory.conversation_repository
        conversation_id = await conversation_repo.create_new_conversation()
        
        if not conversation_id:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to create new conversation"}
            )
        
        return {"conversation_id": conversation_id}
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to create conversation: {str(e)}"}
        )

@app.get("/api/conversations")
async def get_conversations():
    """Returns a list of available conversations for the sidebar."""
    try:
        conversation_repo = repository_factory.conversation_repository
        conversations = await conversation_repo.get_conversation_list()
        return {"conversations": conversations}
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to load conversations: {str(e)}"}
        )

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation with its messages."""
    try:
        logger.info(f"Retrieving conversation: {conversation_id}")
        
        conversation_repo = repository_factory.conversation_repository
        
        # Get the conversation
        conversation = await conversation_repo.find_by_id(conversation_id)
        
        if not conversation:
            logger.warning(f"Conversation not found: {conversation_id}")
            return JSONResponse(
                status_code=404,
                content={"error": f"Conversation not found: {conversation_id}"}
            )
        
        # Convert message objects to dictionaries if they're not already
        messages = []
        for msg in conversation.messages:
            if isinstance(msg, dict):
                messages.append(msg)
            else:
                # If it's a Pydantic model
                messages.append(msg.dict())
        
        # Return in the format expected by frontend
        return {
            "conversation_id": conversation.id,
            "messages": messages,
            "preview": conversation.preview,
            "last_updated": conversation.last_updated.isoformat() if hasattr(conversation.last_updated, "isoformat") else conversation.last_updated
        }
    except Exception as e:
        logger.error(f"Error retrieving conversation: {str(e)}")
        return JSONResponse(
            status_code=500, 
            content={"error": f"Failed to retrieve conversation: {str(e)}"}
        )

@app.post("/api/conversations/save")
async def save_conversation(data: dict):
    """Save a conversation with proper field handling."""
    try:
        conversation_repo = repository_factory.conversation_repository
        
        conv_id = data.get("conversation_id")
        if not conv_id:
            return JSONResponse(
                status_code=400,
                content={"error": "conversation_id is required"}
            )
        
        logger.info(f"Saving conversation: {conv_id}")
        
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
        print("----------------------------------------------------------------------------------------")
        print(conv_id)
        print(type(conv_id))
        print("----------------------------------------------------------------------------------------")
        
        # Check if conversation exists
        existing = await conversation_repo.find_by_id(conv_id)
        
        if existing:
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
            # Use the Conversation model directly
            from app.database.models import Conversation
            
            conversation = Conversation(
                id=conv_id,
                messages=data.get("messages", []),
                preview=data.get("preview", "New Conversation"),
                last_updated=data.get("last_updated", datetime.utcnow())
            )
            
            result = await conversation_repo.create(conversation)
            if not result:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to create conversation"}
                )
        
        logger.info(f"Successfully saved conversation: {conv_id}")
        return {"status": "saved"}
    except Exception as e:
        logger.error(f"Error saving conversation: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to save conversation: {str(e)}"}
        )
    
@app.post("/api/conversations/clear")
async def clear_conversations():
    """Clear all conversations."""
    try:
        logger.info("Clearing all conversations")
        
        conversation_repo = repository_factory.conversation_repository
        
        # Use the MongoDB collection directly for a bulk delete operation
        result = await conversation_repo.collection.delete_many({})
        
        deleted_count = result.deleted_count
        logger.info(f"Deleted {deleted_count} conversations")
        
        if deleted_count > 0:
            return {"message": f"Successfully cleared {deleted_count} conversations"}
        else:
            logger.warning("No conversations found to clear")
            return {"message": "No conversations found to clear"}
            
    except Exception as e:
        logger.error(f"Error clearing conversations: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to clear conversations: {str(e)}"}
        )
    
# Document sharing endpoints
@app.post("/api/documents/share", dependencies=[Depends(get_db)])
async def share_document(
    document_id: str = Form(...),
    owner_id: str = Form(...),
    share_with_user_id: str = Form(...)
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
        if document.owner_id != owner_id:
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
            logger.info(f"Shared document {document_id} with user {share_with_user_id}")
            return {"message": "Document shared successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to share document"}
            )
    
    except Exception as e:
        logger.error(f"Error sharing document: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error sharing document: {str(e)}"}
        )

@app.post("/api/documents/unshare", dependencies=[Depends(get_db)])
async def unshare_document(
    document_id: str = Form(...),
    owner_id: str = Form(...),
    user_id: str = Form(...)
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
        if document.owner_id != owner_id:
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to modify sharing for this document"}
            )
        
        # Unshare document
        success = await app.state.document_repo.unshare_document(document_id, user_id)
        
        if success:
            logger.info(f"Removed sharing for document {document_id} from user {user_id}")
            return {"message": "Document sharing removed successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to remove document sharing"}
            )
    
    except Exception as e:
        logger.error(f"Error removing document sharing: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error removing document sharing: {str(e)}"}
        )

# Migration utility endpoints
@app.post("/api/admin/run-migration", dependencies=[Depends(get_db)])
async def run_migration(background_tasks: BackgroundTasks):
    """Run the data migration from file-based storage to MongoDB."""
    try:
        # Import migration utility
        from app.database.migration_utility import run_migration
        
        # Run migration in background
        background_tasks.add_task(run_migration)
        
        return {"message": "Migration started in background"}
    
    except Exception as e:
        logger.error(f"Error starting migration: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error starting migration: {str(e)}"}
        )

@app.get("/api/admin/migration-status", dependencies=[Depends(get_db)])
async def get_migration_status():
    """Check the status of data migration."""
    try:
        # Import migration utility
        from app.database.migration_utility import migration_utility
        
        # Verify migration
        verification = await migration_utility.verify_migration()
        
        return verification
    
    except Exception as e:
        logger.error(f"Error checking migration status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error checking migration status: {str(e)}"}
        )

# Add endpoint to check Ollama status
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

# Add endpoint to set LLM model
@app.post("/api/set_model", dependencies=[Depends(get_db)])
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

# Add endpoint to get available models
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

# Add endpoint to clear cache
@app.post("/api/clear_cache", dependencies=[Depends(get_db)])
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
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error clearing cache: {str(e)}"}
        )

# Add endpoint to manage knowledge graph
@app.post("/api/knowledge_graph/build", dependencies=[Depends(get_db)])
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
        # This is a simplified example - in a real implementation,
        # you would process document text to extract entities and relationships
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
                
                # Process document content (simplified example)
                # In a real implementation, use NLP to extract entities
                # For simplicity, just extract some keywords
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
        
        logger.info(f"Knowledge graph built with {stats.get('nodes', 0)} nodes and {stats.get('edges', 0)} edges")
        
        return {
            "message": "Knowledge graph built successfully",
            "graph_id": graph_id,
            "stats": stats
        }
    
    except Exception as e:
        logger.error(f"Error building knowledge graph: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error building knowledge graph: {str(e)}"}
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

@app.get("/api/knowledge_graph/stats", dependencies=[Depends(get_db)])
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
    
    except Exception as e:
        logger.error(f"Error getting knowledge graph stats: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting knowledge graph stats: {str(e)}"}
        )

# Add these fixed endpoints to your app/main_mongodb.py file

@app.get("/api/logs")
async def get_logs():
    """Get a list of all log files with timeout protection."""
    try:
        # Set a timeout for database operations
        from asyncio import wait_for, TimeoutError
        
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
            logger.info(f"Found {len(logs)} log files")
            return {"logs": logs}
            
        except TimeoutError:
            logger.error("Timeout fetching log files")
            # Return a fallback response
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            return {
                "logs": [{
                    "filename": f"mongodb_{today}.log",
                    "size": 1024,  # Placeholder size
                    "last_modified": int(datetime.now().timestamp())
                }]
            }
    except Exception as e:
        logger.error(f"Error getting log files: {str(e)}")
        return {"error": f"Error getting log files: {str(e)}"}

@app.get("/api/logs/{filename}")
async def get_log_content(filename: str):
    """Get the content of a specific log file with fallback mechanism."""
    try:
        # Set a timeout for database operations
        from asyncio import wait_for, TimeoutError
        
        # Try to get the logs with a timeout
        try:
            log_repo = repository_factory.log_repository
            content = await wait_for(log_repo.get_log_content(filename), timeout=5.0)
            
            # Return the content
            return {
                "filename": filename,
                "content": content
            }
        except TimeoutError:
            logger.error(f"Timeout fetching log content for {filename}")
            
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
                    except Exception as format_error:
                        log_lines.append(f"Error formatting log: {str(format_error)}")
                
                content = "\n".join(log_lines) if log_lines else f"No logs found for {date_str}"
                
                # Close the MongoDB connection
                client.close()
                
                return {
                    "filename": filename,
                    "content": content
                }
                
            except Exception as direct_error:
                logger.error(f"Direct MongoDB access failed: {str(direct_error)}")
                return {
                    "filename": filename,
                    "content": f"Error retrieving logs: Repository timeout and direct access failed.\n{str(direct_error)}"
                }
                
    except Exception as e:
        logger.error(f"Error reading log file {filename}: {str(e)}")
        return {"error": f"Error reading log file: {str(e)}"}

# Add this debug endpoint to help troubleshoot
@app.get("/api/logs/debug/test")
async def test_log_endpoints():
    """Test endpoint that creates logs and directly retrieves them."""
    try:
        # Generate a few test logs
        logger.warning("Test warning log from debug endpoint")
        logger.error("Test error log from debug endpoint")
        
        # Get the current date
        today = datetime.now().strftime("%Y%m%d")
        filename = f"mongodb_{today}.log"
        
        # Try direct PyMongo access
        import pymongo
        import urllib.parse
        from app.database.config import mongodb_config
        
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
        
    except Exception as e:
        logger.error(f"Debug endpoint error: {str(e)}")
        return {"error": f"Debug endpoint error: {str(e)}"}
    
@app.post("/api/rebuild_index", dependencies=[Depends(get_db)])
async def rebuild_faiss_index():
    """
    Endpoint to rebuild the FAISS index used for vector similarity search.
    
    This endpoint:
    1. Gets the async vector store from the app state
    2. Forces a rebuild of the FAISS index by calling initialize_faiss_index()
    3. Returns success/error message based on the rebuild result
    
    Returns:
        JSON response with success message or error details
    """
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
    
    except Exception as e:
        logger.error(f"Error rebuilding FAISS index: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error rebuilding FAISS index: {str(e)}"}
        )

@app.post("/api/chat/stream")
async def streaming_chat(request: dict):
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
        
        logger.info(f"Starting streaming chat for message: {message[:50]}...")
        
        # Get conversation context if ID provided
        conversation_context = []
        if conversation_id:
            conversation_repo = repository_factory.conversation_repository
            conversation = await conversation_repo.find_by_id(conversation_id)
            
            if conversation:
                # Format conversation context
                for msg in conversation.messages:
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
                                sources=sources
                            )
                        
                        return
                
                # Send final event
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Error in token generator: {str(e)}")
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
    
    except Exception as e:
        logger.error(f"Error in streaming chat endpoint: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Streaming chat error: {str(e)}"}
        )

async def save_streaming_conversation(
    conversation_id: str,
    user_message: str,
    assistant_response: str,
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
            messages = conversation.messages
            messages.append(user_msg)
            messages.append(assistant_msg)
            
            await conversation_repo.update(conversation_id, {
                "messages": messages,
                "preview": user_message[:50] + "..." if len(user_message) > 50 else user_message,
                "last_updated": datetime.utcnow()
            })
        else:
            # Create new conversation
            from app.database.models import Conversation
            
            new_conversation = Conversation(
                id=conversation_id,
                messages=[user_msg, assistant_msg],
                preview=user_message[:50] + "..." if len(user_message) > 50 else user_message,
                last_updated=datetime.utcnow()
            )
            
            await conversation_repo.create(new_conversation)
        
        logger.info(f"Saved streaming conversation: {conversation_id}")
        
    except Exception as e:
        logger.error(f"Error saving streaming conversation: {str(e)}")
    
# Run server
if __name__ == "__main__":
    logger.info("Starting FastAPI server with MongoDB support")
    uvicorn.run("app.main_mongodb:app", host="0.0.0.0", port=8001, reload=True)