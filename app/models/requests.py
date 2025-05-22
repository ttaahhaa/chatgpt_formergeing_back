"""
Pydantic request models for API endpoints.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

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