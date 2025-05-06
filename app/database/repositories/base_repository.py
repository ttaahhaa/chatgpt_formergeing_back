"""
Base repository class providing common database operations.
"""
import logging
from typing import List, Dict, Any, Optional, TypeVar, Generic, Type
from bson import ObjectId
from pydantic import BaseModel

from app.database.config import mongodb_config

T = TypeVar('T', bound=BaseModel)

logger = logging.getLogger(__name__)

class BaseRepository(Generic[T]):
    """Base repository class with common CRUD operations."""
    
    def __init__(self, collection_name: str, model_class: Type[T]):
        """
        Initialize the repository.
        
        Args:
            collection_name: Name of the MongoDB collection
            model_class: Pydantic model class for type validation
        """
        client = mongodb_config.get_async_client()
        self.db = client[mongodb_config.database_name]
        self.collection = self.db[collection_name]
        self.model_class = model_class
        logger.info(f"Initialized repository for collection: {collection_name}")
    
    async def find_by_id(self, id: str) -> Optional[T]:
        """
        Find a document by ID.
        
        Args:
            id: Document ID
            
        Returns:
            Document if found, None otherwise
        """
        try:
            result = await self.collection.find_one({"_id": id})
            if result:
                # Convert MongoDB _id to string id for Pydantic
                result["id"] = str(result.pop("_id"))
                return self.model_class(**result)
            return None
        except Exception as e:
            logger.error(f"Error finding document by ID: {str(e)}")
            return None
    
    async def find(self, query: Dict[str, Any], limit: int = 0, skip: int = 0) -> List[T]:
        """
        Find documents matching a query.
        
        Args:
            query: MongoDB query
            limit: Maximum number of results (0 for unlimited)
            skip: Number of documents to skip
            
        Returns:
            List of matching documents
        """
        try:
            cursor = self.collection.find(query)
            
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            
            results = []
            async for doc in cursor:
                # Convert MongoDB _id to string id for Pydantic
                doc["id"] = str(doc.pop("_id"))
                results.append(self.model_class(**doc))
            
            return results
        except Exception as e:
            logger.error(f"Error finding documents: {str(e)}")
            return []
    
    async def create(self, item: T) -> Optional[str]:
        """
        Create a new document.
        
        Args:
            item: Document to create (Pydantic model or dict)
            
        Returns:
            Document ID if successful, None otherwise
        """
        try:
            # Convert Pydantic model to dict if it's not already a dict
            if hasattr(item, 'dict'):
                item_dict = item.dict()
            else:
                # If it's already a dictionary, use it as is
                item_dict = dict(item)
            
            # Handle ID field (use provided id as _id)
            if "id" in item_dict:
                item_dict["_id"] = item_dict.pop("id")
            
            # Insert document
            result = await self.collection.insert_one(item_dict)
            
            if result and result.inserted_id:
                logger.info(f"Created document with ID: {result.inserted_id}")
                return str(result.inserted_id)
            
            return None
        except Exception as e:
            logger.error(f"Error creating document: {str(e)}")
            return None
    
    async def update(self, id: str, item: Dict[str, Any]) -> bool:
        """
        Update a document.
        
        Args:
            id: Document ID
            item: Fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Handle ID field if present
            if "id" in item:
                del item["id"]
            
            result = await self.collection.update_one(
                {"_id": id},
                {"$set": item}
            )
            
            if result and result.modified_count > 0:
                logger.info(f"Updated document with ID: {id}")
                return True
            
            logger.warning(f"Document with ID {id} was not updated")
            return False
        except Exception as e:
            logger.error(f"Error updating document: {str(e)}")
            return False
    
    async def delete(self, id: str) -> bool:
        """
        Delete a document.
        
        Args:
            id: Document ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.collection.delete_one({"_id": id})
            
            if result and result.deleted_count > 0:
                logger.info(f"Deleted document with ID: {id}")
                return True
            
            logger.warning(f"Document with ID {id} was not deleted")
            return False
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            return False
    
    async def count(self, query: Dict[str, Any] = None) -> int:
        """
        Count documents matching a query.
        
        Args:
            query: MongoDB query (None for all documents)
            
        Returns:
            Document count
        """
        try:
            # Make sure to await the count operation
            return await self.collection.count_documents(query or {})
        except Exception as e:
            logger.error(f"Error counting documents: {str(e)}")
            return 0