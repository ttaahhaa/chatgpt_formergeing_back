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

class ConversationRepository(BaseRepository):
    """Repository for conversation operations."""
    
    def __init__(self, collection):
        """Initialize the conversation repository."""
        super().__init__(collection)
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
            
            # Create new conversation document
            conversation_doc = {
                "id": conv_id,
                "owner_id": owner_id,
                "messages": [],
                "preview": "New Conversation",
                "last_updated": datetime.utcnow()
            }
            
            # Insert directly into MongoDB
            result = await self.collection.insert_one(conversation_doc)
            
            if result.inserted_id:
                logger.info(f"Created new conversation: {conv_id}")
                return conv_id
            
            logger.error("Failed to create conversation")
            return None
        
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
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Update fields to set
            update_fields = {
                "$push": {"messages": message},
                "$set": {"last_updated": datetime.utcnow()}
            }
            
            # Update preview if this is a user message
            if role == "user":
                preview_text = content[:50] + "..." if len(content) > 50 else content
                update_fields["$set"]["preview"] = preview_text
            
            # Update conversation using the id field
            result = await self.collection.update_one(
                {"id": conversation_id},
                update_fields
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
                {"id": conversation_id},  # Changed from _id to id
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
                    "id": 1,
                    "last_updated": 1,
                    "messageCount": {"$size": "$messages"},
                    # Extract first user message as preview if messages exist
                    "preview": {
                        "$cond": {
                            "if": {"$gt": [{"$size": "$messages"}, 0]},
                            "then": {
                                "$let": {
                                    "vars": {
                                        "userMessages": {
                                            "$filter": {
                                                "input": "$messages",
                                                "as": "msg",
                                                "cond": {"$eq": ["$$msg.role", "user"]}
                                            }
                                        }
                                    },
                                    "in": {
                                        "$cond": {
                                            "if": {"$gt": [{"$size": "$$userMessages"}, 0]},
                                            "then": {
                                                "$substr": [
                                                    {"$arrayElemAt": ["$$userMessages.content", 0]}, 
                                                    0, 
                                                    50
                                                ]
                                            },
                                            "else": "New Conversation"
                                        }
                                    }
                                }
                            },
                            "else": "New Conversation"
                        }
                    }
                }}
            ]
            
            cursor = self.collection.aggregate(pipeline)
            results = []
            
            async for doc in cursor:
                results.append({
                    "id": doc["id"],
                    "preview": doc["preview"] + "..." if len(doc["preview"]) >= 50 else doc["preview"],
                    "last_updated": doc["last_updated"],
                    "messageCount": doc["messageCount"]
                })
            
            return results
        except Exception as e:
            logger.error(f"Error getting conversation list: {str(e)}")
            return []
        