"""
Repository for user operations.
"""
import logging
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import hashlib
import os
from motor.motor_asyncio import AsyncIOMotorCollection
from passlib.context import CryptContext

from app.database.models import User
from app.database.config import mongodb_config
from app.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRepository(BaseRepository):
    """Repository for user operations."""
    
    def __init__(self, collection: AsyncIOMotorCollection):
        """Initialize the user repository."""
        super().__init__(collection)
        self.pwd_context = pwd_context
        # Create indexes for username and email
        self._create_indexes()
    
    def _create_indexes(self):
        """Create necessary indexes for the collection."""
        try:
            # Create unique indexes for username and email
            self.collection.create_index("username", unique=True)
            self.collection.create_index("email", unique=True)
            logger.info("Created user collection indexes")
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
    
    async def find_by_username(self, username: str) -> Optional[Dict]:
        """Find a user by username."""
        return await self.find_one({"username": username})
    
    async def find_by_email(self, email: str) -> Optional[Dict]:
        """
        Find a user by email.
        
        Args:
            email: Email address
            
        Returns:
            User if found, None otherwise
        """
        return await self.find_one({"email": email})
    
    async def create_user(self, user_data: Dict) -> Optional[Dict]:
        """Create a new user."""
        # Hash password
        user_data["password"] = self.pwd_context.hash(user_data["password"])
        user_data["created_at"] = datetime.utcnow()
        user_data["is_active"] = True
        
        # Insert user
        result = await self.create(user_data)
        return result
    
    async def update_password(self, user_id: str, new_password: str) -> bool:
        """Update a user's password."""
        hashed_password = self.pwd_context.hash(new_password)
        result = await self.update(
            user_id,
            {
                "password": hashed_password,
                "updated_at": datetime.utcnow()
            }
        )
        return result is not None
    
    async def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate a user with username and password."""
        user = await self.find_one({"username": username})
        if not user:
            return None
        if not self.pwd_context.verify(password, user["password"]):
            return None
        return user
    
    async def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if a user has a specific permission."""
        user = await self.find_by_id(user_id)
        if not user:
            return False
        
        # Admin has all permissions
        if user["role"] == "admin":
            return True
            
        # Check specific permissions
        permissions = user.get("permissions", [])
        return permission in permissions

    async def get_user_permissions(self, user_id: str) -> List[str]:
        """Get all permissions for a user."""
        user = await self.find_by_id(user_id)
        if not user:
            return []
            
        # Admin has all permissions
        if user["role"] == "admin":
            return ["*"]
            
        return user.get("permissions", [])

    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user."""
        result = await self.update(
            user_id,
            {
                "is_active": False,
                "updated_at": datetime.utcnow()
            }
        )
        return result is not None

    async def activate_user(self, user_id: str) -> bool:
        """Activate a user."""
        result = await self.update(
            user_id,
            {
                "is_active": True,
                "updated_at": datetime.utcnow()
            }
        )
        return result is not None

    def _hash_password(self, password: str) -> str:
        """
        Hash a password.
        
        Args:
            password: Plain password
            
        Returns:
            Hashed password
        """
        # Generate a random salt
        salt = os.urandom(16).hex()
        
        # Hash password with salt
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        
        # Return salt:hash format
        return f"{salt}:{hashed}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against a hash.
        
        Args:
            password: Plain password
            password_hash: Hashed password (salt:hash format)
            
        Returns:
            True if password is correct, False otherwise
        """
        try:
            # Split salt and hash
            salt, stored_hash = password_hash.split(":", 1)
            
            # Hash the provided password with the same salt
            hashed = hashlib.sha256((password + salt).encode()).hexdigest()
            
            # Compare hashes
            return hashed == stored_hash
        except Exception:
            return False
