import asyncio
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from app.database.config import mongodb_config
from app.database.models import User
from app.database.repositories.user_repository import UserRepository
import urllib.parse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define roles and their permissions
ROLES = {
    "admin": {
        "permissions": ["*"]
    },
    "chat_user": {
        "permissions": ["chat:stream"]
    },
    "chat_user_with_documents": {
        "permissions": [
            "chat:stream",
            "documents:upload",
            "documents:delete",
            "documents:view",
            "chat:view",
            "chat:create",
            "chat:edit",
            "chat:delete"
        ]
    },
    "settings_user_with_documents": {
        "permissions": [
            "chat:stream",
            "documents:upload",
            "documents:delete",
            "documents:view",
            "chat:view",
            "chat:create",
            "chat:edit",
            "chat:delete",
            "settings:view",
            "settings:edit",
            "model:view",
            "model:change"
        ]
    }
}

# Initial users to create
INITIAL_USERS = [
    # Admin user
    {
        "username": "admin",
        "email": "admin@example.com",
        "password": "admin123",
        "role": "admin",
        "description": "Administrator"
    },
]

# Add 5 chat users (chat only)
for i in range(1, 6):
    INITIAL_USERS.append({
        "username": f"chat_user{i}",
        "email": f"chat_user{i}@example.com",
        "password": "chat123",
        "role": "chat_user",
        "description": f"Chat user {i} (chat only)"
    })

# Add 5 chat users with document access
for i in range(1, 6):
    INITIAL_USERS.append({
        "username": f"doc_user{i}",
        "email": f"doc_user{i}@example.com",
        "password": "doc123",
        "role": "chat_user_with_documents",
        "description": f"Chat user {i} (chat + document access)"
    })

# Add 5 settings users with document access
for i in range(1, 6):
    INITIAL_USERS.append({
        "username": f"settings_user{i}",
        "email": f"settings_user{i}@example.com",
        "password": "settings123",
        "role": "settings_user_with_documents",
        "description": f"Settings user {i} (chat + document + settings access)"
    })

async def init_users():
    """Initialize users in the database."""
    # Initialize client outside try block
    client = None
    try:
        # URL encode username and password
        username = urllib.parse.quote_plus(mongodb_config.username)
        password = urllib.parse.quote_plus(mongodb_config.password)
        
        # Create MongoDB connection string
        mongo_uri = (
            f"mongodb://{username}:{password}@{mongodb_config.host}:{mongodb_config.port}/"
            f"{mongodb_config.database_name}?authSource={mongodb_config.auth_source}"
        )
        
        # Connect to MongoDB
        client = AsyncIOMotorClient(mongo_uri)
        db = client[mongodb_config.database_name]
        
        # Get users collection
        users_collection = db["users"]
        
        # Create user repository
        user_repo = UserRepository(users_collection)
        
        # Clear existing users
        await users_collection.delete_many({})
        logger.info("Cleared existing users")
        
        # Create users
        for user_data in INITIAL_USERS:
            try:
                # Add permissions from role
                user_data["permissions"] = ROLES[user_data["role"]]["permissions"]
                
                # Create user with hashed password
                user = await user_repo.create_user(user_data)
                logger.info(f"Created user: {user['username']}")
            except Exception as e:
                logger.error(f"Error creating user {user_data['username']}: {str(e)}")
        
        logger.info("User initialization completed")
        
    except Exception as e:
        logger.error(f"Error initializing users: {str(e)}")
        raise
    finally:
        # Only close client if it was created
        if client:
            client.close()

if __name__ == "__main__":
    # Run the async function
    asyncio.run(init_users()) 