"""
Repository for conversation operations.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from app.database.models import Conversation, ConversationMessage
from app.database.config import mongodb_config
from app.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class ConversationRepository(BaseRepository[Conversation]):
    """Repository for conversation operations."""
    
    def __init__(self):
        """Initialize the conversation repository."""
        super().__init__(
            collection_name=mongodb_config.conversations_collection,
            model_class=Conversation
        )
        # Create index for last_updated field for sorting
        self._create_indexes()
    
    def _create_indexes(self):
        """Create necessary indexes for the collection."""
        try:
            # Index on last_updated for sorting conversations
            self.collection.create_index("last_updated")
            # Index on owner_id for filtering user conversations
            self.collection.create_index("owner_id")
            logger.info("Created conversation collection indexes")
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
    
    async def find_by_owner(self, owner_id: str, limit: int = 50, skip: int = 0) -> List[Conversation]:
        """
        Find conversations owned by a user.
        
        Args:
            owner_id: Owner user ID
            limit: Maximum number of conversations to return
            skip: Number of conversations to skip
            
        Returns:
            List of conversations
        """
        return await self.find(
            {"owner_id": owner_id},
            limit=limit,
            skip=skip
        )
    
    async def create_new_conversation(self, owner_id: Optional[str] = None) -> Optional[str]:
        """
        Create a new empty conversation.
        
        Args:
            owner_id: Optional owner user ID
            
        Returns:
            Conversation ID if successful, None otherwise
        """
        try:
            # Generate a unique conversation ID
            conv_id = f"conv_{uuid.uuid4()}"
            
            # Create new conversation
            conversation = Conversation(
                id=conv_id,
                owner_id=owner_id,
                messages=[],
                preview="New Conversation",
                last_updated=datetime.utcnow()
            )
            
            return await self.create(conversation)
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            return None
    
    async def add_message(self, conversation_id: str, role: str, content: str) -> bool:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: Conversation ID
            role: Message role ("user" or "assistant")
            content: Message content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create message
            message = ConversationMessage(
                role=role,
                content=content,
                timestamp=datetime.utcnow()
            )
            
            # Update conversation
            result = await self.collection.update_one(
                {"_id": conversation_id},
                {
                    "$push": {"messages": message.dict()},
                    "$set": {
                        "last_updated": datetime.utcnow(),
                        # Update preview if this is a user message
                        "preview": content[:50] + "..." if role == "user" else None
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Added message to conversation {conversation_id}")
                return True
            
            logger.warning(f"Conversation {conversation_id} not found or not updated")
            return False
        except Exception as e:
            logger.error(f"Error adding message: {str(e)}")
            return False
    
    async def clear_messages(self, conversation_id: str) -> bool:
        """
        Clear all messages from a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"_id": conversation_id},
                {
                    "$set": {
                        "messages": [],
                        "last_updated": datetime.utcnow(),
                        "preview": "New Conversation"
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Cleared messages from conversation {conversation_id}")
                return True
            
            logger.warning(f"Conversation {conversation_id} not found or not updated")
            return False
        except Exception as e:
            logger.error(f"Error clearing messages: {str(e)}")
            return False
    
    async def get_conversation_list(self, owner_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get a list of conversations with summary information.
        
        Args:
            owner_id: Optional owner ID to filter by
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation summaries
        """
        try:
            # Build query
            query = {}
            if owner_id:
                query["owner_id"] = owner_id
            
            # Use aggregation pipeline to get summary information
            pipeline = [
                {"$match": query},
                {"$sort": {"last_updated": -1}},
                {"$limit": limit},
                {"$project": {
                    "_id": 1,
                    "preview": 1,
                    "last_updated": 1,
                    "messageCount": {"$size": "$messages"}
                }}
            ]
            
            cursor = self.collection.aggregate(pipeline)
            results = []
            
            async for doc in cursor:
                results.append({
                    "id": doc["_id"],
                    "preview": doc["preview"],
                    "last_updated": doc["last_updated"],
                    "messageCount": doc["messageCount"]
                })
            
            return results
        except Exception as e:
            logger.error(f"Error getting conversation list: {str(e)}")
            return []