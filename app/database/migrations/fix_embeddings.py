"""
One-time migration to fix the embeddings collection.
Run this once to fix existing data.
"""
import logging
from app.database import get_db

logger = logging.getLogger(__name__)

async def migrate_embeddings_collection():
    """
    One-time migration to fix the embeddings collection.
    Run this once to fix existing data.
    """
    from app.database import get_db
    
    db = next(get_db())
    embeddings_collection = db.embeddings
    
    # Drop the problematic unique index
    try:
        embeddings_collection.drop_index("document_id_1")
        print("Dropped unique index on document_id")
    except Exception as e:
        print(f"Could not drop index: {e}")
    
    # Create new compound index
    embeddings_collection.create_index([
        ("document_id", 1),
        ("chunk_index", 1)
    ], unique=True)
    print("Created compound index on (document_id, chunk_index)")
    
    # Update existing embeddings to have chunk_index = 0 if missing
    result = embeddings_collection.update_many(
        {"chunk_index": {"$exists": False}},
        {"$set": {"chunk_index": 0, "chunk_start": 0, "chunk_end": 0}}
    )
    print(f"Updated {result.modified_count} existing embeddings with chunk_index=0")

if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate_embeddings_collection()) 