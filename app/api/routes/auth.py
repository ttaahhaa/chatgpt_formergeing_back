"""
Authentication routes: login, user profile, password management.
"""
import logging
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import get_current_user, get_user_repo
from app.models.responses import UserResponse
from app.utils.jwt_utils import create_access_token, Token, TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["authentication"])

@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_repo = Depends(get_user_repo)
):
    """Authenticate a user and return JWT token."""
    try:
        # Authenticate user
        user = await user_repo.authenticate(form_data.username, form_data.password)
        
        if not user:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid username or password"}
            )
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user["username"], "user_id": user["id"]}
        )
        
        logger.info("User logged in: %s", user['username'])
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    
    except (ValueError, AttributeError) as e:
        logger.error("Error logging in: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Error logging in: {str(e)}"}
        )

@router.get("/me")
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user),
    user_repo = Depends(get_user_repo)
):
    """Get the current user's profile."""
    try:
        user = await user_repo.find_by_id(current_user.user_id)
        
        if not user:
            return JSONResponse(
                status_code=404,
                content={"error": "User not found"}
            )
        
        # Get user permissions
        permissions = await user_repo.get_user_permissions(user["id"])
        
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "permissions": permissions,
            "created_at": user["created_at"]
        }
    
    except (ValueError, AttributeError) as e:
        logger.error("Error retrieving user: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving user: {str(e)}"}
        )

@router.post("/change-password")
async def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    current_user: TokenData = Depends(get_current_user),
    user_repo = Depends(get_user_repo)
):
    """Change a user's password."""
    try:
        # Get user
        user = await user_repo.find_by_id(current_user.user_id)
        
        if not user:
            return JSONResponse(
                status_code=404,
                content={"error": "User not found"}
            )
        
        # Verify current password
        if not await user_repo.authenticate(user["username"], current_password):
            return JSONResponse(
                status_code=401,
                content={"error": "Current password is incorrect"}
            )
        
        # Update password
        success = await user_repo.update_password(user["id"], new_password)
        
        if not success:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to update password"}
            )
        
        logger.info("Password changed for user: %s", user['username'])
        return {"message": "Password changed successfully"}
    
    except (ValueError, AttributeError) as e:
        logger.error("Invalid password format: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid password format: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )