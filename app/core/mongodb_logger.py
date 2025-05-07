# app/core/mongodb_logger.py

import logging
import sys
import os
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
import threading
import time
import queue
import pymongo  # Using direct PyMongo instead of Motor
import urllib.parse  # For URL encoding username/password

class MongoDBLogHandler(logging.Handler):
    """
    Custom logging handler that stores logs in MongoDB using synchronous PyMongo.
    Uses a background thread for processing to avoid blocking the main thread.
    """
    
    def __init__(self, level=logging.WARNING):
        super().__init__(level)
        self.log_queue = queue.Queue()
        self.should_stop = False
        self.repository = None
        self.debug_mode = True
        self.debug_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                      "logs", "mongodb_logger_debug.log")
        
        # Create debug log file
        os.makedirs(os.path.dirname(self.debug_file), exist_ok=True)
        with open(self.debug_file, 'a') as f:
            f.write(f"\n\n--- MongoDB Logger Initialized at {datetime.now()} ---\n")
        
        self._debug("MongoDB logger initialized")
        
        # Start worker thread for processing logs
        self.worker_thread = threading.Thread(target=self._process_logs, daemon=True)
        self.worker_thread.start()

    def _debug(self, message):
        """Write debug message to file."""
        if self.debug_mode:
            try:
                with open(self.debug_file, 'a') as f:
                    f.write(f"{datetime.now()}: {message}\n")
            except Exception as e:
                print(f"Error writing to debug file: {str(e)}", file=sys.stderr)

    def emit(self, record):
        try:
            # Skip logs from the logging system itself to prevent recursion
            if record.name.startswith("app.database.repositories.log_repository"):
                return

            # Format the message
            message = self.format(record)
            
            # Create log entry
            log_entry = {
                "level": record.levelname,
                "message": message,
                "timestamp": datetime.now(),
                "source": record.name,
                "metadata": {
                    "filename": record.filename,
                    "lineno": record.lineno,
                    "funcName": record.funcName,
                    "process": record.process,
                    "thread": record.thread
                }
            }

            # Add to queue for processing
            self._debug(f"Buffering log: {record.levelname} - {record.getMessage()}")
            self.log_queue.put(log_entry)
                
        except Exception as e:
            self._debug(f"Error in emit: {str(e)}\n{traceback.format_exc()}")
            print(f"Error in MongoDB log handler emit: {str(e)}", file=sys.stderr)

    def _init_repository(self):
        """Initialize direct connection to MongoDB."""
        try:
            # Import configuration with minimal imports
            from app.database.config import mongodb_config
            
            # Connect to MongoDB directly using PyMongo
            if hasattr(mongodb_config, 'username') and hasattr(mongodb_config, 'password') and mongodb_config.username and mongodb_config.password:
                # URL encode username and password
                username = urllib.parse.quote_plus(mongodb_config.username)
                password = urllib.parse.quote_plus(mongodb_config.password)
                mongo_uri = (
                    f"mongodb://{username}:{password}@{mongodb_config.host}:{mongodb_config.port}/"
                    f"{mongodb_config.database_name}?authSource={mongodb_config.auth_source}"
                )
                self._debug(f"Using authenticated connection to MongoDB (username: {username})")
            else:
                # No authentication
                mongo_uri = f"mongodb://{mongodb_config.host}:{mongodb_config.port}/{mongodb_config.database_name}"
                self._debug("Using non-authenticated connection to MongoDB")
            
            # Try direct connection
            client = pymongo.MongoClient(mongo_uri)
            
            # Test connection
            client.server_info()  # This will raise an exception if connection fails
            
            # Get database and collection
            db = client[mongodb_config.database_name]
            self.collection = db["logs"]
            
            # Ensure indexes
            self.collection.create_index("timestamp")
            self.collection.create_index("level")
            
            self._debug(f"Connected directly to MongoDB collection: logs in database: {mongodb_config.database_name}")
            return True
            
        except Exception as e:
            self._debug(f"Error initializing direct MongoDB connection: {str(e)}\n{traceback.format_exc()}")
            print(f"Error connecting to MongoDB: {str(e)}", file=sys.stderr)
            
            # Try alternative connection without credentials
            try:
                self._debug("Trying alternative connection without credentials...")
                from app.database.config import mongodb_config
                mongo_uri = f"mongodb://{mongodb_config.host}:{mongodb_config.port}/{mongodb_config.database_name}"
                client = pymongo.MongoClient(mongo_uri)
                client.server_info()
                db = client[mongodb_config.database_name]
                self.collection = db["logs"]
                self._debug("Alternative connection successful")
                return True
            except Exception as alt_e:
                self._debug(f"Alternative connection also failed: {str(alt_e)}")
                return False

    def _process_logs(self):
        """Background thread to process logs."""
        # Wait a bit before starting to allow application to initialize
        time.sleep(2)
        
        # Initialize MongoDB connection
        if not self._init_repository():
            self._debug("Failed to initialize MongoDB connection, worker thread stopping")
            return
            
        self._debug("Worker thread started successfully")
        
        while not self.should_stop:
            try:
                # Process logs in batch
                logs_to_process = []
                
                # Get all available logs from queue (non-blocking)
                try:
                    while len(logs_to_process) < 50:  # Process up to 50 at a time
                        log_entry = self.log_queue.get(block=True, timeout=0.5)
                        logs_to_process.append(log_entry)
                        self.log_queue.task_done()
                except queue.Empty:
                    # No more logs in queue, continue with what we have
                    pass
                
                # If we have logs to process
                if logs_to_process:
                    self._store_logs_batch(logs_to_process)
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.1)
                
            except Exception as e:
                self._debug(f"Error in worker thread: {str(e)}\n{traceback.format_exc()}")
                # Sleep longer after error
                time.sleep(1)
    
    def _store_logs_batch(self, logs):
        """Store a batch of logs in MongoDB."""
        if not logs:
            return
            
        try:
            self._debug(f"Processing batch of {len(logs)} logs")
            
            # Convert logs to MongoDB documents
            documents = []
            for log in logs:
                # Create document with MongoDB _id
                doc = {
                    "_id": f"log_{uuid.uuid4()}",
                    "level": log["level"],
                    "message": log["message"],
                    "timestamp": log["timestamp"],
                    "source": log["source"],
                    "metadata": log["metadata"]
                }
                documents.append(doc)
            
            # Insert using PyMongo
            if documents:
                result = self.collection.insert_many(documents)
                self._debug(f"Successfully stored {len(result.inserted_ids)}/{len(documents)} logs directly")
                
        except Exception as e:
            self._debug(f"Error storing log batch: {str(e)}\n{traceback.format_exc()}")
            # Try to store logs one by one to salvage what we can
            self._store_logs_individually(logs)
    
    def _store_logs_individually(self, logs):
        """Fallback method to store logs one by one if batch insert fails."""
        try:
            successful = 0
            for log in logs:
                try:
                    doc = {
                        "_id": f"log_{uuid.uuid4()}",
                        "level": log["level"],
                        "message": log["message"],
                        "timestamp": log["timestamp"],
                        "source": log["source"],
                        "metadata": log["metadata"]
                    }
                    self.collection.insert_one(doc)
                    successful += 1
                except Exception as individual_error:
                    self._debug(f"Failed to store individual log: {str(individual_error)}")
            
            self._debug(f"Individual storage completed: {successful}/{len(logs)} logs stored")
        except Exception as e:
            self._debug(f"Error in individual storage: {str(e)}")

    def flush(self):
        """
        Flush any remaining logs.
        This is a no-op as logs are processed by the background thread.
        """
        pass

    def close(self):
        """Close the handler."""
        self.should_stop = True
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)  # Wait up to 2 seconds for thread to finish
        self._debug("MongoDB logger closed")
        super().close()

def test_mongodb_logger():
    """Test the MongoDB logger directly."""
    try:
        print("Testing MongoDB logger...")
        
        # Initialize the handler
        handler = MongoDBLogHandler(level=logging.INFO)
        
        # Wait for handler to initialize
        time.sleep(3)
        
        # Create test logs
        for i in range(3):
            formatted_message = f"Test log entry #{i+1} - {datetime.now().isoformat()}"
            record = logging.LogRecord(
                name="test_logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg=formatted_message,
                args=(),
                exc_info=None
            )
            handler.emit(record)
            print(f"Emitted test log: {formatted_message}")
        
        # Wait for processing
        print("Waiting for logs to be processed...")
        time.sleep(5)
        
        # Close handler
        handler.close()
        
        print(f"Test complete. Check debug log at: {handler.debug_file}")
        return True
    except Exception as e:
        print(f"Test failed: {str(e)}")
        traceback.print_exc()
        return False

# Allow direct testing
if __name__ == "__main__":
    test_mongodb_logger()