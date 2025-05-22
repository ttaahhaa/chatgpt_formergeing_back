"""
Pydantic response models for API endpoints.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

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