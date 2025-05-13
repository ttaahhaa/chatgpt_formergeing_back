"""
Repository for document operations.
"""
import logging
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from app.database.models import Document
from app.database.config import mongodb_config
from app.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class DocumentRepository(BaseRepository):
    """Repository for document operations."""
    
    def __init__(self, collection):
        """Initialize with MongoDB collection."""
        super().__init__(collection)
    
    async def find_by_filename(self, filename: str, owner_id: Optional[str] = None) -> Optional[Document]:
        """
        Find a document by filename.
        
        Args:
            filename: Document filename
            owner_id: Optional owner ID to filter by
            
        Returns:
            Document if found, None otherwise
        """
        query = {"filename": filename}
        if owner_id:
            query["owner_id"] = owner_id
        
        results = await self.find(query, limit=1)
        return results[0] if results else None
    
    async def find_by_owner(self, owner_id: str) -> List[Document]:
        """
        Find all documents owned by a user.
        
        Args:
            owner_id: Owner user ID
            
        Returns:
            List of documents
        """
        return await self.find({"owner_id": owner_id})
    
    async def find_shared_with(self, user_id: str) -> List[Document]:
        """
        Find all documents shared with a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of documents
        """
        return await self.find({"shared_with": user_id})
    
    async def find_accessible(self, user_id: str) -> List[Dict]:
        """Find documents accessible to a user."""
        try:
            # Find documents where user is owner or in shared_with
            query = {
                "$or": [
                    {"owner_id": user_id},
                    {"shared_with": user_id}
                ]
            }
            return await self.find(query)
        except Exception as e:
            print(f"Error finding accessible documents: {str(e)}")
            return []
    
    async def add_document(self, document_data: Dict[str, Any], owner_id: Optional[str] = None) -> Optional[str]:
        """
        Add a new document.
        
        Args:
            document_data: Document data
            owner_id: Optional owner user ID
            
        Returns:
            Document ID if successful, None otherwise
        """
        try:
            # Generate a unique ID if not provided
            if "id" not in document_data:
                document_data["id"] = f"doc_{uuid.uuid4()}"
            
            # Set owner if provided
            if owner_id:
                document_data["owner_id"] = owner_id
            
            # Create document model and save
            document = Document(**document_data)
            return await self.create(document)
        except Exception as e:
            logger.error(f"Error adding document: {str(e)}")
            return None
    
    async def share_document(self, document_id: str, user_id: str) -> bool:
        """Share a document with a user."""
        try:
            result = await self.collection.update_one(
                {"id": document_id},
                {"$addToSet": {"shared_with": user_id}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error sharing document: {str(e)}")
            return False
    
    async def unshare_document(self, document_id: str, user_id: str) -> bool:
        """Remove a user's access to a shared document."""
        try:
            result = await self.collection.update_one(
                {"id": document_id},
                {"$pull": {"shared_with": user_id}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error unsharing document: {str(e)}")
            return False

    async def create(self, document: Dict[str, Any]) -> Optional[str]:
        """Create a new document."""
        try:
            logger.info(f"Creating document in MongoDB: {document}")
            result = await self.collection.insert_one(document)
            logger.info(f"Document created in MongoDB with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating document in MongoDB: {str(e)}")
            return None

    async def find(self, query: Dict[str, Any], limit: int = 0) -> List[Dict]:
        """Find documents matching the query."""
        try:
            cursor = self.collection.find(query)
            if limit > 0:
                cursor = cursor.limit(limit)
            documents = await cursor.to_list(length=limit if limit > 0 else None)
            # Convert Pydantic models to dictionaries if needed
            return [doc.dict() if hasattr(doc, "dict") else doc for doc in documents]
        except Exception as e:
            logger.error(f"Error finding documents: {str(e)}")
            return []
