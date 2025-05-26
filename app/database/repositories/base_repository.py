"""
Base repository class providing common database operations.
"""
import logging
from typing import List, Dict, Any, Optional, TypeVar, Generic, Type, Union
from bson import ObjectId
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorCollection
from datetime import datetime
import uuid

from app.database.config import mongodb_config

T = TypeVar('T', bound=BaseModel)

logger = logging.getLogger(__name__)

class BaseRepository(Generic[T]):
    """Base repository class for MongoDB operations."""
    
    def __init__(self, collection: AsyncIOMotorCollection):
        """Initialize the repository with a MongoDB collection."""
        self.collection = collection
    
    async def create(self, data: Union[Dict, BaseModel]) -> Optional[Dict]:
        """Create a new document."""
        try:
            logger.info(f"Attempting to create document with data: {data}")
            
            # Convert Pydantic model to dict if needed
            if isinstance(data, BaseModel):
                data = data.model_dump()
            
            # Add ID if not present
            if "id" not in data:
                data["id"] = str(uuid.uuid4())
                logger.info(f"Generated new ID: {data['id']}")
            
            # Add timestamps
            data["created_at"] = datetime.utcnow()
            data["updated_at"] = datetime.utcnow()
            
            # Insert document
            logger.info(f"Inserting document into collection: {self.collection.name}")
            result = await self.collection.insert_one(data)
            
            if result.inserted_id:
                logger.info(f"Successfully created document with ID: {data['id']}")
                return data
            
            logger.error("Document creation failed - no inserted_id returned")
            return None
            
        except Exception as e:
            logger.error(f"Error creating document: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            return None
    
    async def find_by_id(self, id: str) -> Optional[Dict]:
        """Find a document by ID."""
        try:
            return await self.collection.find_one({"id": id})
        except Exception as e:
            print(f"Error finding document: {str(e)}")
            return None
    
    async def find(self, query: Dict, limit: int = 0) -> List[Dict]:
        """Find documents matching query."""
        try:
            cursor = self.collection.find(query)
            if limit > 0:
                cursor = cursor.limit(limit)
            return await cursor.to_list(length=limit if limit > 0 else None)
        except Exception as e:
            print(f"Error finding documents: {str(e)}")
            return []
    
    async def find_one(self, query: Dict) -> Optional[Dict]:
        """Find a single document matching query."""
        try:
            return await self.collection.find_one(query)
        except Exception as e:
            print(f"Error finding document: {str(e)}")
            return None
    
    async def update(self, id: str, data: Dict) -> Optional[Dict]:
        """Update a document."""
        try:
            # Add update timestamp
            data["updated_at"] = datetime.utcnow()
            
            # Update document
            result = await self.collection.update_one(
                {"id": id},
                {"$set": data}
            )
            
            if result.modified_count > 0:
                return await self.find_by_id(id)
            return None
        except Exception as e:
            print(f"Error updating document: {str(e)}")
            return None
    
    async def delete(self, id: str) -> bool:
        """Delete a document."""
        try:
            result = await self.collection.delete_one({"id": id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting document: {str(e)}")
            return False
    
    async def count(self, query: Dict = None) -> int:
        """Count documents matching query."""
        try:
            return await self.collection.count_documents(query or {})
        except Exception as e:
            print(f"Error counting documents: {str(e)}")
            return 0
    
    async def delete_all(self) -> bool:
        """Delete all documents from the collection."""
        try:
            result = await self.collection.delete_many({})
            logger.info(f"Deleted {result.deleted_count} documents from collection")
            return True
        except Exception as e:
            logger.error(f"Error deleting all documents: {str(e)}")
            return False