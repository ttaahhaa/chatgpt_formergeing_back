"""
Repository for user settings operations.
"""
import logging
from typing import Dict, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection
from app.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class UserSettingsRepository(BaseRepository):
    """Repository for user settings operations."""
    
    def __init__(self, collection: AsyncIOMotorCollection):
        """Initialize the user settings repository."""
        super().__init__(collection)
        self._create_indexes()
    
    def _create_indexes(self):
        """Create necessary indexes for the collection."""
        try:
            # Create unique index for user_id
            self.collection.create_index("user_id", unique=True)
            logger.info("Created user settings collection indexes")
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
    
    async def find_by_user_id(self, user_id: str) -> Optional[Dict]:
        """Find settings for a specific user."""
        return await self.find_one({"user_id": user_id})
    
    async def update(self, user_id: str, settings_data: Dict) -> bool:
        """Update settings for a user."""
        settings_data["updated_at"] = datetime.utcnow()
        result = await self.collection.update_one(
            {"user_id": user_id},
            {"$set": settings_data}
        )
        return result.modified_count > 0
    
    async def create(self, settings_data: Dict) -> Optional[Dict]:
        """Create new settings for a user."""
        settings_data["created_at"] = datetime.utcnow()
        settings_data["updated_at"] = datetime.utcnow()
        result = await self.collection.insert_one(settings_data)
        if result.inserted_id:
            return await self.find_by_id(str(result.inserted_id))
        return None 