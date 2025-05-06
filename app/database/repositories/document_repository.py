"""
Repository for document operations.
"""
import logging
from typing import List, Dict, Any, Optional
import uuid

from app.database.models import Document
from app.database.config import mongodb_config
from app.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class DocumentRepository(BaseRepository[Document]):
    """Repository for document operations."""
    
    def __init__(self):
        """Initialize the document repository."""
        super().__init__(
            collection_name=mongodb_config.documents_collection,
            model_class=Document
        )
    
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
    
    async def find_accessible(self, user_id: str) -> List[Document]:
        """
        Find all documents accessible by a user (owned or shared).
        
        Args:
            user_id: User ID
            
        Returns:
            List of documents
        """
        return await self.find({
            "$or": [
                {"owner_id": user_id},
                {"shared_with": user_id}
            ]
        })
    
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
        """
        Share a document with a user.
        
        Args:
            document_id: Document ID
            user_id: User ID to share with
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"_id": document_id},
                {"$addToSet": {"shared_with": user_id}}
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error sharing document: {str(e)}")
            return False
    
    async def unshare_document(self, document_id: str, user_id: str) -> bool:
        """
        Remove a user's access to a shared document.
        
        Args:
            document_id: Document ID
            user_id: User ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"_id": document_id},
                {"$pull": {"shared_with": user_id}}
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error unsharing document: {str(e)}")
            return False
