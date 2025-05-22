"""
Chat routes: chat processing and streaming responses.
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse as FastAPIStreamingResponse

from app.api.dependencies import (
    get_current_user, check_permission, get_llm_chain, 
    get_vector_store, get_streaming_llm, get_conversation_repo
)
from app.models.requests import QueryRequest, ChatRequest
from app.models.responses import QueryResponse, ChatResponse
from app.utils.jwt_utils import TokenData
from app.database.models import Conversation
from app.database.repositories.factory import repository_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    vector_store = Depends(get_vector_store),
    llm_chain = Depends(get_llm_chain),
    conversation_repo = Depends(get_conversation_repo)
):
    """Process a query against the document store."""
    try:
        logger.info("Processing query: %s", request.query)
        
        # Retrieve relevant documents
        results = await vector_store.async_store.query(request.query, top_k=5)
        
        if not results:
            logger.warning("No relevant documents found for query")
        
        # Generate response with sources
        llm_response = llm_chain.query_with_sources(
            request.query, 
            results
        )
        # Save to conversation if ID provided
        if request.conversation_id:
            # Add user message
            await conversation_repo.add_message(
                conversation_id=request.conversation_id,
                role="user",
                content=request.query
            )
            
            # Add assistant response
            await conversation_repo.add_message(
                conversation_id=request.conversation_id,
                role="assistant",
                content=llm_response["response"]
            )
        
        # Create response
        response = QueryResponse(
            response=llm_response["response"],
            sources=llm_response["sources"],
            conversation_id=request.conversation_id
        )
        
        logger.info("Query processed successfully")
        return JSONResponse(
            status_code=410,
            content={
                "warning": "This endpoint is deprecated. Please use /api/chat instead.",
                "data": response.dict()
            }
        )
    
    except (ValueError, AttributeError) as e:
        logger.error("Invalid query format: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid query format: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@router.post("/chat")
async def chat(
    request: dict,
    current_user: TokenData = Depends(check_permission("chat:send")),
    llm_chain = Depends(get_llm_chain),
    vector_store = Depends(get_vector_store)
):
    """Process a chat message and return a response."""
    try:
        # Extract message and conversation ID from request
        message = request.get("message", "")
        conversation_id = request.get("conversation_id")
        mode = request.get("mode", "auto")  # Get the mode parameter
        
        if not message:
            return JSONResponse(
                status_code=400,
                content={"error": "Message is required"}
            )
        
        # Get conversation history if conversation_id is provided
        conversation_context = []
        if conversation_id:
            conversation_repo = repository_factory.conversation_repository
            conversation = await conversation_repo.find_by_id(conversation_id)
            
            if conversation:
                # Check ownership
                if conversation.owner_id != current_user.user_id:
                    return JSONResponse(
                        status_code=403,
                        content={"error": "You don't have permission to access this conversation"}
                    )
                    
                # Convert ConversationMessage objects to dictionaries if needed
                for msg in conversation.messages:
                    # Check if it's already a dict or needs conversion
                    if isinstance(msg, dict):
                        # Make sure the dict has the required fields
                        if "role" in msg and "content" in msg:
                            conversation_context.append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })
                    else:
                        # It's a Pydantic model, extract the fields
                        conversation_context.append({
                            "role": msg.role,
                            "content": msg.content
                        })
        
        # Determine if we should use documents based on the mode
        use_documents = mode == "documents_only" or mode == "auto"
        
        # Get response from LLM
        if use_documents:
            # Get relevant documents
            results = await vector_store.async_store.query(message, top_k=5)
            
            if not results:
                logger.warning("No relevant documents found for query")
            
            # Generate response with sources
            llm_response = llm_chain.query_with_sources(
                message, 
                results
            )
            response = llm_response["response"]
            sources = llm_response["sources"]
        else:
            # Generate general response
            response = llm_chain.generate_response(message, conversation_context)
            sources = None
        
        # Save the conversation if conversation_id is provided
        if conversation_id:
            # Save user message
            user_message = {
                "role": "user",
                "content": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Save assistant response
            assistant_message = {
                "role": "assistant",
                "content": response,
                "timestamp": datetime.utcnow().isoformat(),
                "sources": sources if sources else None
            }
            
            # Add messages to conversation
            conversation_repo = repository_factory.conversation_repository
            conversation = await conversation_repo.find_by_id(conversation_id)
            
            if conversation:
                # Check ownership
                if conversation.owner_id != current_user.user_id:
                    return JSONResponse(
                        status_code=403,
                        content={"error": "You don't have permission to modify this conversation"}
                    )
                    
                # Get existing messages
                messages = conversation.messages
                
                # Add new messages
                messages.append(user_message)
                messages.append(assistant_message)
                
                # Update conversation
                await conversation_repo.update(conversation_id, {
                    "messages": messages,
                    "preview": message[:50] + "..." if len(message) > 50 else message,
                    "last_updated": datetime.utcnow()
                })
            else:
                # Create new conversation
                conversation_data = {
                    "id": conversation_id,
                    "owner_id": current_user.user_id,
                    "messages": [user_message, assistant_message],
                    "preview": message[:50] + "..." if len(message) > 50 else message,
                    "last_updated": datetime.utcnow()
                }
                
                # Use the Conversation model to create a new conversation
                conversation_obj = Conversation(**conversation_data)
                await conversation_repo.create(conversation_obj)
        
        # Return response
        return {
            "response": response,
            "sources": sources,
            "conversation_id": conversation_id
        }
    except (ValueError, AttributeError) as e:
        logger.error("Invalid request format: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid request format: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except (IOError, OSError) as e:
        logger.error("File operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"File operation error: {str(e)}"}
        )

@router.post("/chat/stream")
async def streaming_chat(
    request: dict,
    current_user: TokenData = Depends(check_permission("chat:stream")),
    streaming_llm = Depends(get_streaming_llm),
    vector_store = Depends(get_vector_store)
):
    """Stream chat responses token by token."""
    try:
        # Extract message and conversation ID from request
        message = request.get("message", "")
        conversation_id = request.get("conversation_id")
        mode = request.get("mode", "auto")
        
        if not message:
            return JSONResponse(
                status_code=400,
                content={"error": "Message is required"}
            )
        
        logger.info("Starting streaming chat for message: %s...", message[:50])
        
        # Get conversation context if ID provided
        conversation_context = []
        if conversation_id:
            conversation_repo = repository_factory.conversation_repository
            conversation = await conversation_repo.find_by_id(conversation_id)
            
            if conversation:
                # Use correct way to access messages
                messages = conversation["messages"] if isinstance(conversation, dict) else conversation.messages
                for msg in messages:
                    if isinstance(msg, dict):
                        if "role" in msg and "content" in msg:
                            conversation_context.append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })
                    else:
                        conversation_context.append({
                            "role": msg.role,
                            "content": msg.content
                        })
        
        # Determine if we should use documents
        sources = []
        use_documents = mode == "documents_only" or mode == "auto"
        
        if use_documents:
            # Use existing vector store from app state
            relevant_docs = await vector_store.async_store.query(message, top_k=5)
            
            # Format sources
            sources = [{
                "document": doc.get("filename", "Unknown"),
                "content": doc.get("content", ""),
                "relevance": doc.get("score", 0.0),
                "page": doc.get("metadata", {}).get("page", 1)
            } for doc in relevant_docs]
        
        # Create token generator
        async def token_generator():
            """Generate tokens from LLM and save conversation."""
            response_text = ""
            try:
                # Stream the response
                async for token_data in streaming_llm.stream_chat(
                    message=message,
                    conversation_context=conversation_context,
                    sources=sources
                ):
                    if "token" in token_data:
                        response_text += token_data["token"]
                        yield f"data: {json.dumps({'token': token_data['token']})}\n\n"
                    elif "error" in token_data:
                        yield f"data: {json.dumps({'error': token_data['error']})}\n\n"
                        return
                    elif token_data.get("done", False):
                        # Send completion with sources
                        yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"
                        
                        # Save conversation after completion
                        if conversation_id:
                            await save_streaming_conversation(
                                conversation_id=conversation_id,
                                user_message=message,
                                assistant_response=response_text,
                                current_user=current_user,
                                sources=sources
                            )
                        
                        return
                
                # Send final event
                yield "data: [DONE]\n\n"
                
            except (ConnectionError, RuntimeError) as e:
                logger.error("Streaming error: %s", str(e))
                yield f"data: {json.dumps({'error': f'Streaming error: {str(e)}'})}\n\n"
                yield "data: [DONE]\n\n"
        
        # Return streaming response
        return FastAPIStreamingResponse(
            token_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable Nginx buffering
            }
        )
    
    except (ValueError, AttributeError) as e:
        logger.error("Invalid request format: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid request format: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except (IOError, OSError) as e:
        logger.error("Streaming error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Streaming error: {str(e)}"}
        )

async def save_streaming_conversation(
    conversation_id: str,
    user_message: str,
    assistant_response: str,
    current_user: TokenData,
    sources: list = None
) -> None:
    """Save streaming conversation after completion."""
    try:
        conversation_repo = repository_factory.conversation_repository
        
        # Get existing conversation or create new
        conversation = await conversation_repo.find_by_id(conversation_id)
        
        # Prepare messages
        user_msg = {
            "role": "user",
            "content": user_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        assistant_msg = {
            "role": "assistant",
            "content": assistant_response,
            "timestamp": datetime.utcnow().isoformat(),
            "sources": sources if sources else None
        }
        
        if conversation:
            # Update existing conversation
            # Create a new list with existing messages plus new ones
            existing_messages = conversation.messages if hasattr(conversation, 'messages') else []
            if isinstance(conversation, dict):
                existing_messages = conversation.get('messages', [])
            
            # Create new list with all messages
            messages = list(existing_messages)  # Create a new list
            messages.append(user_msg)
            messages.append(assistant_msg)
            
            await conversation_repo.update(conversation_id, {
                "messages": messages,
                "preview": user_message[:50] + "..." if len(user_message) > 50 else user_message,
                "last_updated": datetime.utcnow()
            })
        else:
            # Create new conversation
            conversation_data = {
                "id": conversation_id,
                "owner_id": current_user.user_id,
                "messages": [user_msg, assistant_msg],
                "preview": user_message[:50] + "..." if len(user_message) > 50 else user_message,
                "last_updated": datetime.utcnow()
            }
            
            # Use the Conversation model to create a new conversation
            conversation_obj = Conversation(**conversation_data)
            await conversation_repo.create(conversation_obj)
        
        logger.info("Saved streaming conversation: %s", conversation_id)
        
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
    except (ValueError, AttributeError) as e:
        logger.error("Invalid conversation data: %s", str(e))
    except (IOError, OSError) as e:
        logger.error("File operation error: %s", str(e))