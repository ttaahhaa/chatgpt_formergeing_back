"""
MongoDB data models for Document QA Assistant.
Defines schemas for all collections.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from zoneinfo import ZoneInfo  # For timezone support

class User(BaseModel):
    """User model for authentication and access control."""
    username: str
    email: str
    password_hash: str  # Store hashed password, never plaintext
    created_at: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
    last_login: Optional[datetime] = None
    is_active: bool = True
    role: str = "user"  # Options: "user", "admin"
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "user1",
                "email": "user1@example.com",
                "password_hash": "[hashed_password]",
                "created_at": "2023-01-01T00:00:00",
                "last_login": "2023-01-02T12:30:45",
                "is_active": True,
                "role": "user"
            }
        }
    )

class Document(BaseModel):
    """Document model for storing document metadata and content."""
    id: str  # Unique identifier
    filename: str
    extension: str
    content: str  # Full document text content
    metadata: Dict[str, Any] = {}  # Flexible metadata
    owner_id: Optional[str] = None  # Owner user ID
    shared_with: List[str] = []  # List of user IDs with access
    created_at: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "doc_12345",
                "filename": "example.pdf",
                "extension": ".pdf",
                "content": "Document content here...",
                "metadata": {
                    "size": 1024,
                    "type": "document",
                    "pages": 5
                },
                "owner_id": "user_12345",
                "shared_with": [],
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
        }
    )

class Embedding(BaseModel):
    """Document embedding model for vector search."""
    document_id: str  # Reference to document
    embedding: List[float]  # Vector embedding
    embedding_model: str = "arabert"  # Model used to generate embedding
    created_at: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "doc_12345",
                "embedding": [0.1, 0.2, 0.3, 0.4],  # Truncated for brevity
                "embedding_model": "arabert",
                "created_at": "2023-01-01T00:00:00"
            }
        }
    )

class ConversationMessage(BaseModel):
    """Individual message in a conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if hasattr(v, "isoformat") else str(v)
        }
    )

class Conversation(BaseModel):
    """Conversation model for storing chat history."""
    id: str  # Unique conversation ID
    owner_id: Optional[str] = None  # Owner user ID
    messages: List[Dict[str, Any]] = []  # Changed from List[ConversationMessage] to List[Dict]
    preview: str = "New Conversation"  # Preview/title for UI
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if hasattr(v, "isoformat") else str(v)
        },
        json_schema_extra={
            "example": {
                "id": "conv_12345",
                "owner_id": "user_12345",
                "messages": [
                    {
                        "role": "user",
                        "content": "How does the system work?",
                        "timestamp": "2023-01-01T12:00:00"
                    },
                    {
                        "role": "assistant",
                        "content": "The system works by...",
                        "timestamp": "2023-01-01T12:00:05"
                    }
                ],
                "preview": "How does the system work?",
                "last_updated": "2023-01-01T12:00:05"
            }
        }
    )

class Log(BaseModel):
    """Log entry model for storing application logs."""
    id: str
    level: str  # ERROR, WARNING, INFO, DEBUG
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
    source: str = "application"
    metadata: Dict[str, Any] = {}
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "log_12345",
                "level": "INFO",
                "message": "Application started",
                "timestamp": "2025-04-29T15:19:56",
                "source": "application",
                "metadata": {
                    "user_id": "user_123",
                    "ip": "127.0.0.1"
                }
            }
        }
    )
        
class KnowledgeGraphNode(BaseModel):
    """Node in the knowledge graph."""
    id: str  # Unique node ID
    label: str  # Node label/name
    type: str = "entity"  # Node type
    properties: Dict[str, Any] = {}  # Additional node properties

class KnowledgeGraphEdge(BaseModel):
    """Edge in the knowledge graph."""
    source: str  # Source node ID
    target: str  # Target node ID
    relation: str  # Edge label/relationship type
    properties: Dict[str, Any] = {}  # Additional edge properties

class KnowledgeGraph(BaseModel):
    """Knowledge graph model."""
    owner_id: Optional[str] = None  # Owner user ID
    nodes: List[KnowledgeGraphNode] = []
    edges: List[KnowledgeGraphEdge] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
