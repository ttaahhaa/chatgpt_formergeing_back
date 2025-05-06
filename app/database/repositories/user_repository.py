"""
Repository for user operations.
"""
import logging
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import hashlib
import os

from app.database.models import User
from app.database.config import mongodb_config
from app.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class UserRepository(BaseRepository[User]):
    """Repository for user operations."""
    
    def __init__(self):
        """Initialize the user repository."""
        super().__init__(
            collection_name=mongodb_config.users_collection,
            model_class=User
        )
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
    
    async def find_by_username(self, username: str) -> Optional[User]:
        """
        Find a user by username.
        
        Args:
            username: Username
            
        Returns:
            User if found, None otherwise
        """
        results = await self.find({"username": username}, limit=1)
        return results[0] if results else None
    
    async def find_by_email(self, email: str) -> Optional[User]:
        """
        Find a user by email.
        
        Args:
            email: Email address
            
        Returns:
            User if found, None otherwise
        """
        results = await self.find({"email": email}, limit=1)
        return results[0] if results else None
    
    async def create_user(self, username: str, email: str, password: str, role: str = "user") -> Optional[str]:
        """
        Create a new user.
        
        Args:
            username: Username
            email: Email address
            password: Plain password (will be hashed)
            role: User role
            
        Returns:
            User ID if successful, None otherwise
        """
        try:
            # Check if username or email already exists
            existing_user = await self.find_by_username(username)
            if existing_user:
                logger.warning(f"Username {username} already exists")
                return None
            
            existing_email = await self.find_by_email(email)
            if existing_email:
                logger.warning(f"Email {email} already exists")
                return None
            
            # Generate a unique user ID
            user_id = f"user_{uuid.uuid4()}"
            
            # Hash the password
            password_hash = self._hash_password(password)
            
            # Create user
            user = User(
                id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                created_at=datetime.utcnow(),
                is_active=True,
                role=role
            )
            
            return await self.create(user)
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return None
    
    async def update_password(self, user_id: str, new_password: str) -> bool:
        """
        Update a user's password.
        
        Args:
            user_id: User ID
            new_password: New password (will be hashed)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Hash the new password
            password_hash = self._hash_password(new_password)
            
            return await self.update(user_id, {"password_hash": password_hash})
        except Exception as e:
            logger.error(f"Error updating password: {str(e)}")
            return False
    
    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            User if authentication successful, None otherwise
        """
        try:
            # Find user by username
            user = await self.find_by_username(username)
            if not user:
                return None
            
            # Check if account is active
            if not user.is_active:
                logger.warning(f"Attempt to authenticate inactive user: {username}")
                return None
            
            # Verify password
            if self._verify_password(password, user.password_hash):
                # Update last login time
                await self.update(user.id, {"last_login": datetime.utcnow()})
                return user
            
            return None
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            return None
    
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
