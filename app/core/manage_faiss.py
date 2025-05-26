"""
Script to manage FAISS index - build, rebuild, or clear.

python -m app.core.manage_faiss [command]
Where [command] can be one of:
    build: Build or rebuild the FAISS index
    clear: Clear the FAISS cache
    status: Check the status of the FAISS index
"""
import asyncio
import os
import tempfile
import logging

from .vector_store_hybrid import get_hybrid_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def build_index():
    """Build or rebuild the FAISS index."""
    logger.info("Starting FAISS index build...")
    
    vector_store = get_hybrid_vector_store()
    
    # Force rebuild
    success = await vector_store.async_store.initialize_faiss_index(force_rebuild=True)
    
    if success:
        logger.info("FAISS index built successfully!")
        logger.info(f"Index contains {vector_store.async_store.faiss_index.ntotal} vectors")
    else:
        logger.error("Failed to build FAISS index")

async def clear_cache():
    """Clear the FAISS cache files."""
    import shutil
    
    cache_dir = os.path.join(tempfile.gettempdir(), "faiss_cache")
    
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
        logger.info(f"Cleared FAISS cache at {cache_dir}")
    else:
        logger.info("No cache to clear")

async def check_status():
    """Check the status of the FAISS index."""
    vector_store = get_hybrid_vector_store()
    
    if vector_store.async_store.index_initialized:
        logger.info("FAISS index is initialized")
        logger.info(f"Index contains {vector_store.async_store.faiss_index.ntotal} vectors")
        logger.info(f"Document map contains {len(vector_store.async_store.document_id_map)} entries")
    else:
        logger.info("FAISS index is not initialized")
    
    # Check cache
    cache_dir = os.path.join(tempfile.gettempdir(), "faiss_cache")
    if os.path.exists(os.path.join(cache_dir, "faiss_index.bin")):
        logger.info("FAISS cache exists")
    else:
        logger.info("No FAISS cache found")

async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="FAISS Index Management")
    parser.add_argument("command", choices=["build", "clear", "status"], 
                      help="Command to execute")
    
    args = parser.parse_args()
    
    if args.command == "build":
        await build_index()
    elif args.command == "clear":
        await clear_cache()
    elif args.command == "status":
        await check_status()

if __name__ == "__main__":
    asyncio.run(main()) 