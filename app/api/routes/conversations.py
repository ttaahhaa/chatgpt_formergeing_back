"""
Conversation management routes: create, list, get, save, delete conversations.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.api.dependencies import get_current_user, check_permission, get_conversation_repo, get_user_repo
from app.utils.jwt_utils import TokenData
from app.database.models import Conversation
from app.database.repositories.factory import repository_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

@router.post("/new")
async def new_conversation(
    current_user: TokenData = Depends(check_permission("chat:create")),
    conversation_repo = Depends(get_conversation_repo)
):
    """Create a new conversation."""
    try:
        # Ensure we have a valid user_id
        if not current_user or not current_user.user_id:
            return JSONResponse(
                status_code=401,
                content={"error": "User not authenticated"}
            )

        conversation_id = await conversation_repo.create_new_conversation(current_user.user_id)
        
        if not conversation_id:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to create new conversation"}
            )
        
        return {"conversation_id": conversation_id}
    except (ValueError, AttributeError) as e:
        logger.error("Invalid user data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid user data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@router.get("")
async def get_conversations(
    current_user: TokenData = Depends(get_current_user),
    user_repo = Depends(get_user_repo),
    conversation_repo = Depends(get_conversation_repo)
):
    """Returns a list of available conversations for the sidebar."""
    try:
        # Check if user has permission to view conversations
        has_permission = await user_repo.check_permission(current_user.user_id, "chat:view")
        if not has_permission:
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to view conversations"}
            )

        conversations = await conversation_repo.get_conversation_list(current_user.user_id)
        return {"conversations": conversations}
    except (ValueError, AttributeError) as e:
        logger.error("Invalid user data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid user data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: TokenData = Depends(get_current_user),
    user_repo = Depends(get_user_repo),
    conversation_repo = Depends(get_conversation_repo)
):
    """Get a specific conversation with its messages."""
    try:
        logger.info("Retrieving conversation: %s", conversation_id)
        
        # Check if user has permission to view conversations
        has_permission = await user_repo.check_permission(current_user.user_id, "chat:view")
        if not has_permission:
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to view conversations"}
            )
        
        # Get the conversation
        conversation = await conversation_repo.find_by_id(conversation_id)
        
        if not conversation:
            logger.warning("Conversation not found: %s", conversation_id)
            return JSONResponse(
                status_code=404,
                content={"error": f"Conversation not found: {conversation_id}"}
            )
            
        # Check ownership
        owner_id = conversation.get("owner_id") if isinstance(conversation, dict) else conversation.owner_id
        if owner_id != current_user.user_id:
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to view this conversation"}
            )
        
        # Return in the format expected by frontend
        return {
            "conversation_id": conversation["id"] if isinstance(conversation, dict) else conversation.id,
            "messages": conversation["messages"] if isinstance(conversation, dict) else conversation.messages,
            "preview": conversation["preview"] if isinstance(conversation, dict) else conversation.preview,
            "last_updated": conversation["last_updated"] if isinstance(conversation, dict) else conversation.last_updated
        }
    except (ValueError, AttributeError) as e:
        logger.error("Invalid conversation data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid conversation data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@router.post("/save")
async def save_conversation(
    data: dict,
    current_user: TokenData = Depends(get_current_user),
    conversation_repo = Depends(get_conversation_repo)
):
    """Save a conversation with proper field handling."""
    try:
        # Ensure we have a valid user_id
        if not current_user or not current_user.user_id:
            return JSONResponse(
                status_code=401,
                content={"error": "User not authenticated"}
            )

        conv_id = data.get("conversation_id")
        if not conv_id:
            return JSONResponse(
                status_code=400,
                content={"error": "conversation_id is required"}
            )
        
        logger.info("Saving conversation: %s", conv_id)
        
        # Ensure all required fields exist
        if "messages" not in data and "history" in data:
            # Convert history to messages (frontend may use different field names)
            data["messages"] = data.pop("history")
        elif "messages" not in data:
            # Ensure messages exists
            data["messages"] = []
            
        # Ensure preview exists
        if not data.get("preview"):
            data["preview"] = "New Conversation"
            
        # Ensure last_updated exists
        if not data.get("last_updated"):
            data["last_updated"] = datetime.utcnow()
            
        # Check if conversation exists
        existing = await conversation_repo.find_by_id(conv_id)
        
        if existing:
            # Get owner_id safely whether it's a dict or model
            owner_id = existing.get("owner_id") if isinstance(existing, dict) else getattr(existing, "owner_id", None)
            
            # Check ownership
            if owner_id != current_user.user_id:
                return JSONResponse(
                    status_code=403,
                    content={"error": "You don't have permission to edit this conversation"}
                )
                
            # Update existing conversation
            update_data = {
                "messages": data.get("messages", []),
                "preview": data.get("preview", "Conversation"),
                "last_updated": data.get("last_updated", datetime.utcnow())
            }
            
            success = await conversation_repo.update(conv_id, update_data)
            if not success:
                return JSONResponse(
                    status_code=500,
                    content={"error": f"Failed to update conversation {conv_id}"}
                )
        else:
            # Create new conversation
            conversation_data = {
                "id": conv_id,
                "owner_id": current_user.user_id,
                "messages": data.get("messages", []),
                "preview": data.get("preview", "New Conversation"),
                "last_updated": data.get("last_updated", datetime.utcnow())
            }
            
            # Create new conversation using the repository
            result = await conversation_repo.create(conversation_data)
            if not result:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to create conversation"}
                )
        
        logger.info("Successfully saved conversation: %s", conv_id)
        return {"status": "saved"}
    except (ValueError, AttributeError) as e:
        logger.error("Invalid conversation data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid conversation data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@router.post("/clear")
async def clear_conversations(
    current_user: TokenData = Depends(check_permission("chat:delete")),
    conversation_repo = Depends(get_conversation_repo)
):
    """Clear all conversations."""
    try:
        logger.info("Clearing all conversations")
        
        # Use the MongoDB collection directly for a bulk delete operation
        result = await conversation_repo.collection.delete_many({"owner_id": current_user.user_id})
        
        deleted_count = result.deleted_count
        logger.info("Deleted %d conversations", deleted_count)
        
        if deleted_count > 0:
            return {"message": f"Successfully cleared {deleted_count} conversations"}
        else:
            logger.warning("No conversations found to clear")
            return {"message": "No conversations found to clear"}
            
    except (ValueError, AttributeError) as e:
        logger.error("Invalid user data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid user data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: TokenData = Depends(check_permission("chat:delete")),
    conversation_repo = Depends(get_conversation_repo)
):
    """Delete a single conversation by ID."""
    try:
        logger.info("Deleting conversation: %s", conversation_id)
        
        # Get the conversation first to check ownership
        conversation = await conversation_repo.find_by_id(conversation_id)
        
        if not conversation:
            logger.warning("Conversation not found: %s", conversation_id)
            return JSONResponse(
                status_code=404,
                content={"error": f"Conversation not found: {conversation_id}"}
            )
        
        # Check ownership
        owner_id = conversation.get("owner_id") if isinstance(conversation, dict) else conversation.owner_id
        if owner_id != current_user.user_id:
            logger.warning("User %s attempted to delete conversation %s owned by %s", 
                         current_user.user_id, conversation_id, owner_id)
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to delete this conversation"}
            )
        
        # Delete the conversation
        result = await conversation_repo.delete(conversation_id)
        
        if result:
            logger.info("Successfully deleted conversation: %s", conversation_id)
            return {"message": "Conversation deleted successfully"}
        else:
            logger.error("Failed to delete conversation: %s", conversation_id)
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to delete conversation"}
            )
            
    except (ValueError, AttributeError) as e:
        logger.error("Invalid conversation data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid conversation data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )