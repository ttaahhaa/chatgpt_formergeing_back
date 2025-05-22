"""
System routes: status, logs, models, and configuration.
"""
import logging
import platform
import sys
import pymongo
import urllib.parse
from datetime import datetime, timedelta
from asyncio import wait_for, TimeoutError as AsyncTimeoutError
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
import psutil

from app.api.dependencies import (
    get_current_user, check_permission, get_llm_chain, 
    get_document_repo, get_embedding_repo, get_conversation_repo
)
from app.core.embeddings import Embeddings
from app.database.repositories.factory import repository_factory
from app.database.config import mongodb_config
from app.utils.jwt_utils import TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["system"])

@router.get("/status")
async def get_status(
    document_repo = Depends(get_document_repo),
    embedding_repo = Depends(get_embedding_repo),
    conversation_repo = Depends(get_conversation_repo),
    llm_chain = Depends(get_llm_chain)
):
    """Get system status information.
    
    This endpoint collects and returns various system status metrics:
    1. Document count from MongoDB
    2. LLM (Language Model) availability status and current model
    3. Embedding model status
    4. MongoDB statistics (docs, embeddings, conversations)
    5. System information (OS, memory usage, Python version)
    
    Returns:
        JSON with status metrics or error response
    """
    try:
        logger.info("Retrieving system status")

        # Step 1: Get document count from MongoDB
        document_count = await document_repo.count({})

        # Step 2: Check LLM status
        llm_status = "unavailable"
        current_model = "unknown"
        try:
            ollama_status = llm_chain.check_ollama_status()
            if ollama_status.get("status") == "available":
                llm_status = "available"
                if ollama_status.get("models"):
                    current_model = ollama_status["models"][0]
        except (ConnectionError, RuntimeError) as e:
            logger.error("LLM status check failed: %s", str(e))

        # Step 3: Check embedding model status
        embedding_status = "unavailable"
        try:
            embedding_model = Embeddings()
            model_status = embedding_model.check_model_status()
            embedding_status = model_status.get("status", "unavailable")
        except (ConnectionError, RuntimeError) as e:
            logger.error("Embedding status check failed: %s", str(e))

        # Step 4: MongoDB stats
        mongo_stats = {
            "documents": document_count,
            "embeddings": await embedding_repo.count({}),
            "conversations": await conversation_repo.count({})
        }

        # Step 5: System info
        system_info = {
            "os": platform.system(),
            "architecture": platform.machine(), 
            "python_version": sys.version.split()[0],
            "app_version": "1.0.0"
        }

        memory_usage = f"{psutil.Process().memory_info().rss / (1024 * 1024):.2f} MB"

        # Final response
        status_data = {
            "llm_status": llm_status,
            "embeddings_status": embedding_status,
            "current_model": current_model,
            "document_count": document_count,
            "database_stats": mongo_stats,
            "memory_usage": memory_usage,
            "system_info": system_info
        }

        logger.info("Status retrieved successfully")
        return status_data

    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid data format: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Invalid data format: {str(e)}"}
        )

@router.get("/check_ollama")
async def check_ollama(llm_chain = Depends(get_llm_chain)):
    """Check Ollama LLM service status."""
    try:
        logger.info("Checking Ollama status")
        status = llm_chain.check_ollama_status()
        logger.info("Ollama status: %s", status)
        return status
    except (ConnectionError, RuntimeError) as e:
        logger.error("Ollama service error: %s", str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "error": f"Ollama service error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid Ollama response: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"status": "unavailable", "error": f"Invalid Ollama response: {str(e)}"}
        )

@router.post("/set_model")
async def set_model(
    request: dict,
    current_user: TokenData = Depends(check_permission("model:change"))
):
    """Set the user's preferred LLM model."""
    try:
        if "model" not in request:
            return JSONResponse(
                status_code=400,
                content={"error": "No model specified"}
            )
        
        model = request.get("model")
        
        # Get user settings repository
        settings_repo = repository_factory.user_settings_repository
        
        # Update or create user settings
        settings = await settings_repo.find_by_user_id(current_user.user_id)
        if settings:
            await settings_repo.update(current_user.user_id, {
                "preferred_model": model,
                "updated_at": datetime.utcnow()
            })
        else:
            await settings_repo.create({
                "user_id": current_user.user_id,
                "preferred_model": model
            })
        
        return {"message": f"Model updated to {model}"}
    except (ValueError, AttributeError) as e:
        logger.error("Invalid model data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid model data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Model service error: %s", str(e))
        return JSONResponse(
            status_code=503,
            content={"error": f"Model service error: {str(e)}"}
        )

@router.get("/models")
async def get_models(
    current_user: TokenData = Depends(check_permission("model:view")),
    llm_chain = Depends(get_llm_chain)
):
    """Get available LLM models and user's preferred model."""
    try:
        # Get available models from Ollama
        ollama_status = llm_chain.check_ollama_status()
        models = ollama_status.get("models", [])
        
        # Get user's preferred model
        settings_repo = repository_factory.user_settings_repository
        user_settings = await settings_repo.find_by_user_id(current_user.user_id)
        preferred_model = user_settings.get("preferred_model") if user_settings else "mistral:latest"
        
        return {
            "models": models,
            "current_model": preferred_model
        }
    except (ConnectionError, RuntimeError) as e:
        logger.error("Model service error: %s", str(e))
        return JSONResponse(
            status_code=503,
            content={"error": f"Model service error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid model data: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Invalid model data: {str(e)}"}
        )

@router.get("/user/preferred-model")
async def get_user_preferred_model(
    current_user: TokenData = Depends(get_current_user)
):
    """Get the current user's preferred model."""
    try:
        # Get user settings repository
        settings_repo = repository_factory.user_settings_repository
        
        # Get user's settings
        user_settings = await settings_repo.find_by_user_id(current_user.user_id)
        
        # Return preferred model or default
        preferred_model = user_settings.get("preferred_model") if user_settings else "mistral:latest"
        
        return {
            "preferred_model": preferred_model
        }
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=503,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid user data: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Invalid user data: {str(e)}"}
        )

@router.get("/logs")
async def get_logs():
    """Get a list of all log files with timeout protection."""
    try:
        # Wrap the repository call with a timeout
        try:
            # Get log repository
            log_repo = repository_factory.log_repository
            
            # Attempt to get log files with a 5-second timeout
            logs = await wait_for(log_repo.get_log_files(), timeout=5.0)
            
            # If no logs found, return empty list
            if not logs:
                logger.warning("No log files found")
                return {"logs": []}
                
            # Add debug information
            logger.info("Found %d log files", len(logs))
            return {"logs": logs}
            
        except AsyncTimeoutError:
            logger.error("Timeout fetching log files")
            # Return a fallback response
            current_date = datetime.now().strftime("%Y%m%d")
            return {
                "logs": [{
                    "filename": f"mongodb_{current_date}.log",
                    "size": 1024,  # Placeholder size
                    "last_modified": int(datetime.now().timestamp())
                }]
            }
    except (ValueError, AttributeError) as e:
        logger.error("Invalid log data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid log data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@router.get("/logs/{filename}")
async def get_log_content(filename: str):
    """Get the content of a specific log file with fallback mechanism."""
    try:
        # Try to get the logs with a timeout
        try:
            log_repo = repository_factory.log_repository
            content = await wait_for(log_repo.get_log_content(filename), timeout=5.0)
            
            # Return the content
            return {
                "filename": filename,
                "content": content
            }
        except AsyncTimeoutError:
            logger.error("Timeout fetching log content for %s", filename)
            
            # Query MongoDB directly as a fallback
            try:
                # Use direct PyMongo access as a fallback
                import re
                
                # Extract date from filename
                date_match = re.search(r'mongodb_(\d{8})\.log', filename)
                if not date_match:
                    return {"content": f"Invalid filename format: {filename}"}
                
                date_str = date_match.group(1)
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                
                # Create datetime objects for start and end of day
                start_date = datetime(year, month, day)
                end_date = start_date + timedelta(days=1)
                
                # Set up direct MongoDB connection
                username = urllib.parse.quote_plus(mongodb_config.username)
                password = urllib.parse.quote_plus(mongodb_config.password)
                mongo_uri = (
                    f"mongodb://{username}:{password}@{mongodb_config.host}:{mongodb_config.port}/"
                    f"{mongodb_config.database_name}?authSource={mongodb_config.auth_source}"
                )
                
                client = pymongo.MongoClient(mongo_uri)
                db = client[mongodb_config.database_name]
                collection = db["logs"]
                
                # Query for logs on the specified day
                cursor = collection.find({
                    "timestamp": {
                        "$gte": start_date,
                        "$lt": end_date
                    }
                }).sort("timestamp", 1)
                
                # Format logs
                log_lines = []
                for doc in cursor:
                    try:
                        timestamp = doc.get("timestamp")
                        if isinstance(timestamp, datetime):
                            timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        
                        level = doc.get("level", "INFO")
                        source = doc.get("source", "unknown")
                        message = doc.get("message", "")
                        
                        log_line = f"{timestamp} - {level} - {source} - {message}"
                        log_lines.append(log_line)
                    except (ValueError, AttributeError) as format_error:
                        log_lines.append(f"Error formatting log: {str(format_error)}")
                
                content = "\n".join(log_lines) if log_lines else f"No logs found for {date_str}"
                
                # Close the MongoDB connection
                client.close()
                
                return {
                    "filename": filename,
                    "content": content
                }
                
            except (ConnectionError, RuntimeError) as direct_error:
                logger.error("Direct MongoDB access failed: %s", str(direct_error))
                return {
                    "filename": filename,
                    "content": f"Error retrieving logs: Repository timeout and direct access failed.\n{str(direct_error)}"
                }
                
    except (ValueError, AttributeError) as e:
        logger.error("Invalid log data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid log data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@router.get("/logs/debug/test")
async def test_log_endpoints():
    """Test endpoint that creates logs and directly retrieves them."""
    try:
        # Generate a few test logs
        logger.warning("Test warning log from debug endpoint")
        logger.error("Test error log from debug endpoint")
        
        # Get the current date
        current_date = datetime.now().strftime("%Y%m%d")
        filename = f"mongodb_{current_date}.log"
        
        # Try direct PyMongo access
        
        # Set up direct MongoDB connection
        username = urllib.parse.quote_plus(mongodb_config.username)
        password = urllib.parse.quote_plus(mongodb_config.password)
        mongo_uri = (
            f"mongodb://{username}:{password}@{mongodb_config.host}:{mongodb_config.port}/"
            f"{mongodb_config.database_name}?authSource={mongodb_config.auth_source}"
        )
        
        client = pymongo.MongoClient(mongo_uri)
        db = client[mongodb_config.database_name]
        collection = db["logs"]
        
        # Get log count
        log_count = collection.count_documents({})
        
        # Get a few sample logs
        sample_logs = list(collection.find().sort("timestamp", -1).limit(5))
        sample_log_data = []
        
        for log in sample_logs:
            sample_log_data.append({
                "level": log.get("level"),
                "message": log.get("message"),
                "timestamp": str(log.get("timestamp")),
                "source": log.get("source")
            })
        
        # Close the MongoDB connection
        client.close()
        
        return {
            "status": "success",
            "log_count": log_count,
            "sample_logs": sample_log_data,
            "today_filename": filename
        }
        
    except (ConnectionError, RuntimeError) as e:
        logger.error("Debug endpoint error: %s", str(e))
        return {"error": f"Debug endpoint error: {str(e)}"}