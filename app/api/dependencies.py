"""
Common dependencies for FastAPI routes.
Authentication, permissions, and other shared dependencies.

This module provides FastAPI dependencies for:
1. Authentication using JWT tokens
2. Permission checking
3. Component access through dependency injection
4. Error handling and logging

The module implements a clean dependency injection pattern that allows routes
to access application components and services in a type-safe and maintainable way.
"""
import logging
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt

from app.utils.jwt_utils import verify_token, TokenData

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication - used for JWT token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    Get the current authenticated user from the JWT token.
    
    This dependency extracts and validates the JWT token from the request,
    returning the user data if valid. It's used as a dependency in routes
    that require authentication.
    
    Args:
        token (str): JWT token from the request header
        
    Returns:
        TokenData: User data extracted from the token
        
    Raises:
        HTTPException: 
            - 401 if token is invalid or missing user data
            - 500 for unexpected errors
    """
    try:
        token_data = verify_token(token)
        if not token_data or not token_data.user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials: missing user data"
            )
        return token_data
    except jwt.PyJWTError as exc:
        logger.error("Authentication error: Invalid token - %s", str(exc))
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        ) from exc
    except HTTPException as exc:
        # Re-raise HTTP exceptions from verify_token
        raise exc
    except Exception as exc:
        logger.error("Unexpected authentication error: %s", str(exc))
        raise HTTPException(
            status_code=500,
            detail="Internal server error during authentication"
        ) from exc

def check_permission(permission: str):
    """
    Check if the current user has the required permission.
    
    This is a factory function that creates a dependency for checking user permissions.
    It's used in routes that require specific permissions.
    
    Args:
        permission (str): The permission to check for (e.g., 'admin', 'read', 'write')
        
    Returns:
        A dependency function that checks the user's permission.
        
    Raises:
        HTTPException: 
            - 403 if user doesn't have required permission
            - 500 for permission check errors
    """
    async def _check_permission(current_user: TokenData = Depends(get_current_user)):
        try:
            # Import components only when needed to avoid circular imports
            from app.config.settings import components
            has_permission = await components.user_repo.check_permission(current_user.user_id, permission)
            if not has_permission:
                raise HTTPException(
                    status_code=403,
                    detail="Not enough permissions"
                )
            return current_user
        except (ValueError, AttributeError) as e:
            logger.error("Permission check error: %s", str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Error checking permissions: {str(e)}"
            ) from e
    return _check_permission

# Component dependencies - import components only when called to avoid circular imports
def get_document_repo():
    """
    Get document repository dependency.
    
    Returns:
        DocumentRepository: Instance of the document repository
    """
    from app.config.settings import components
    return components.document_repo

def get_user_repo():
    """Get user repository."""
    from app.config.settings import components
    return components.user_repo

def get_conversation_repo():
    """Get conversation repository."""
    from app.config.settings import components
    return components.conversation_repo

def get_embedding_repo():
    """Get embedding repository."""
    from app.config.settings import components
    return components.embedding_repo

def get_vector_store():
    """Get vector store."""
    from app.config.settings import components
    return components.vector_store

def get_llm_chain():
    """Get LLM chain."""
    from app.config.settings import components
    return components.llm_chain

def get_streaming_llm():
    """Get streaming LLM."""
    from app.config.settings import components
    return components.streaming_llm

def get_document_loader():
    """Get document loader."""
    from app.config.settings import components
    return components.document_loader