import os
import logging
import tempfile
from typing import Dict, List, Optional, Any
from pathlib import Path
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import uuid
import json
import asyncio

# Setup logging
from app.utils.logging_utils import setup_logging
from app.core.vector_store_hybrid import get_hybrid_vector_store
from app.core.mongodb_logger import MongoDBLogHandler

# Set up logging directories and filenames
today = datetime.now().strftime("%Y%m%d")
base_dir = os.path.dirname(os.path.dirname(__file__))
logs_dir = os.path.join(base_dir, "logs")
os.makedirs(logs_dir, exist_ok=True)

log_file = os.path.join(logs_dir, f"app_mongodb_{today}.log")

# Setup standard file logger (INFO and above)
logger = setup_logging(log_file=log_file, log_level="INFO", app_name="app_mongodb")
logger.info("MongoDB API Service starting")

# Setup MongoDB log handler (store WARNING and above to MongoDB only)
mongo_handler = MongoDBLogHandler(level=logging.WARNING)
mongo_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Attach MongoDB handler to root logger
root_logger = logging.getLogger()
root_logger.addHandler(mongo_handler)

# Import MongoDB and core components
from app.database import initialize_database
from app.database.repositories.factory import repository_factory
from app.core.vector_store_mongodb import get_vector_store
from app.core.document_loader import DocumentLoader
from app.core.llm import LLMChain
from app.core.hybrid_retrieval import HybridRetriever

# Create FastAPI app
app = FastAPI(title="Document QA Assistant API with MongoDB")

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

# Store components in app state
app.state.document_loader = document_loader
app.state.vector_store = vector_store
app.state.llm_chain = llm_chain
app.state.retriever = retriever
logger.info("Core components initialized successfully")

# Get repositories
app.state.document_repo = repository_factory.document_repository
app.state.embedding_repo = repository_factory.embedding_repository
app.state.conversation_repo = repository_factory.conversation_repository
app.state.user_repo = repository_factory.user_repository

# Create data models
class QueryRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None

class QueryResponse(BaseModel):
    response: str
    sources: Optional[List[Dict[str, Any]]] = None
    conversation_id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    mode: Optional[str] = "auto"  # auto, documents_only, general_knowledge

class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[Dict[str, Any]]] = None
    conversation_id: Optional[str] = None

class UserRequest(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
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

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        logger.info("Initializing database connection")
        initialized = await initialize_database()
        if not initialized:
            logger.error("Failed to initialize database")
        else:
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown."""
    try:
        logger.info("Closing database connections")
        from app.database import close_database_connections
        await close_database_connections()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

# API routes
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Document QA Assistant API with MongoDB is running"}

@app.get("/api/status", dependencies=[Depends(get_db)])
async def get_status():
    """Get system status information."""
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
    """Upload a document to the system."""
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
    """Query documents and get a response."""
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
        return response
    
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
            
            # Generate response with document context
            response_with_sources = llm.query_with_sources(message, relevant_docs)
            response = response_with_sources["response"]
            sources = response_with_sources["sources"]
        else:
            # Just use the LLM without document context
            response = llm.generate_response(message, conversation_context)
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

@app.get("/api/logs")
async def get_logs():
    """Get a list of all log files."""
    try:
        log_repo = repository_factory.log_repository
        logs = await log_repo.get_log_files()
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Error getting log files: {str(e)}")
        return {"error": f"Error getting log files: {str(e)}"}

@app.get("/api/logs/{filename}")
async def get_log_content(filename: str):
    """Get the content of a specific log file."""
    try:
        log_repo = repository_factory.log_repository
        content = await log_repo.get_log_content(filename)
        
        return {
            "filename": filename,
            "content": content
        }
    except Exception as e:
        logger.error(f"Error reading log file {filename}: {str(e)}")
        return {"error": f"Error reading log file: {str(e)}"}

@app.post("/api/rebuild_index", dependencies=[Depends(get_db)])
async def rebuild_faiss_index():
    """Rebuild the FAISS index."""
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
    
# Run server
if __name__ == "__main__":
    logger.info("Starting FastAPI server with MongoDB support")
    uvicorn.run("app.main_mongodb:app", host="0.0.0.0", port=8001, reload=True)