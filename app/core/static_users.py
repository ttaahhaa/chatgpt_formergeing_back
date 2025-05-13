from typing import Dict, Optional
from datetime import datetime
import uuid
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Static users data
STATIC_USERS = {
    "admin": {
        "id": str(uuid.uuid4()),
        "username": "admin",
        "password": pwd_context.hash("admin123"),
        "role": "admin",
        "created_at": datetime.utcnow()
    },
    "user1": {
        "id": str(uuid.uuid4()),
        "username": "user1",
        "password": pwd_context.hash("user123"),
        "role": "user",
        "created_at": datetime.utcnow()
    },
    "user2": {
        "id": str(uuid.uuid4()),
        "username": "user2",
        "password": pwd_context.hash("user123"),
        "role": "user",
        "created_at": datetime.utcnow()
    },
    "editor": {
        "id": str(uuid.uuid4()),
        "username": "editor",
        "password": pwd_context.hash("editor123"),
        "role": "editor",
        "created_at": datetime.utcnow()
    },
    "viewer": {
        "id": str(uuid.uuid4()),
        "username": "viewer",
        "password": pwd_context.hash("viewer123"),
        "role": "viewer",
        "created_at": datetime.utcnow()
    }
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_user(username: str) -> Optional[Dict]:
    """Get a user by username."""
    return STATIC_USERS.get(username)

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Authenticate a user with username and password."""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["password"]):
        return None
    return user 