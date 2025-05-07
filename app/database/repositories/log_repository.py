# app/database/repositories/log_repository.py

import logging
import sys
import os
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timedelta
import traceback

from app.database.models import Log
from app.database.config import mongodb_config
from app.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class LogRepository(BaseRepository[Log]):
    """Repository for log operations."""
    
    def __init__(self):
        super().__init__(
            collection_name="logs",
            model_class=Log
        )
        self._create_indexes()
    
    def _create_indexes(self):
        try:
            self.collection.create_index("timestamp")
            self.collection.create_index("level")
            # Avoid logging index creation to MongoDB to prevent recursion
            if self.collection.name != "logs":
                logger.info("Created log collection indexes")
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")

    async def add_log(self, level: str, message: str, source: str = "application", metadata: Dict[str, Any] = None) -> Optional[str]:
        try:
            log_id = f"log_{uuid.uuid4()}"
            log = Log(
                id=log_id,
                level=level,
                message=message,
                timestamp=datetime.utcnow(),
                source=source,
                metadata=metadata or {}
            )

            # Do not log the creation of logs to avoid recursion
            return await self.create(log)
        except Exception as e:
            print(f"Error adding log: {str(e)}", file=sys.stderr)
            return None
    
    async def get_log_files(self) -> List[Dict[str, Any]]:
        """
        Get a list of all logs grouped by day (simulating log files).
        
        Returns:
            List of dictionaries with log file information
        """
        try:
            # Use aggregation to group logs by day and get stats
            pipeline = [
                {
                    "$group": {
                        "_id": {
                            "$dateToString": {
                                "format": "%Y%m%d",
                                "date": "$timestamp"
                            }
                        },
                        "count": {"$sum": 1},
                        "size": {"$sum": {"$strLenCP": "$message"}},
                        "last_modified": {"$max": "$timestamp"}
                    }
                },
                {"$sort": {"_id": -1}}  # Sort by date, newest first
            ]
            
            cursor = self.collection.aggregate(pipeline)
            logs = []
            
            async for doc in cursor:
                # Convert to seconds since epoch for last_modified
                last_modified_timestamp = int(doc["last_modified"].timestamp())
                
                logs.append({
                    "filename": f"mongodb_{doc['_id']}.log",
                    "size": doc["size"],
                    "last_modified": last_modified_timestamp
                })
            
            return logs
        except Exception as e:
            logger.error(f"Error getting log files: {str(e)}")
            return []
    
    async def get_log_content(self, filename: str) -> str:
        """
        Get the content of logs for a specific day.
        
        Args:
            filename: Log filename (format: mongodb_YYYYMMDD.log)
            
        Returns:
            Formatted log content as string
        """
        try:
            # Extract date from filename
            import re
            
            date_match = re.search(r'mongodb_(\d{8})\.log', filename)
            if not date_match:
                return f"Invalid filename format: {filename}"
            
            date_str = date_match.group(1)
            
            # Parse date string
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            
            # Create datetime objects for start and end of day
            start_date = datetime(year, month, day)
            end_date = start_date + timedelta(days=1)
            
            # Format for debug output
            debug_output = f"Retrieving logs for date range: {start_date} to {end_date}\n"
            
            # Use direct PyMongo access for more reliable querying
            collection = self.collection
            
            # Query logs for that day
            logs = []
            try:
                # Find records in the given date range
                cursor = collection.find({
                    "timestamp": {
                        "$gte": start_date,
                        "$lt": end_date
                    }
                }).sort("timestamp", 1)  # Sort by timestamp ascending
                
                async for doc in cursor:
                    try:
                        # Convert MongoDB document to formatted string
                        timestamp = doc.get("timestamp").strftime("%Y-%m-%d %H:%M:%S")
                        level = doc.get("level", "INFO")
                        source = doc.get("source", "unknown")
                        message = doc.get("message", "")
                        
                        # Create formatted log line
                        log_line = f"{timestamp} - {level} - {source} - {message}"
                        logs.append(log_line)
                    except Exception as e:
                        logs.append(f"Error formatting log entry: {str(e)}")
            except Exception as e:
                debug_output += f"Error querying MongoDB: {str(e)}\n{traceback.format_exc()}\n"
                
            # If no logs found, try direct method
            if not logs:
                debug_output += "No logs found using datetime query, trying alternative method...\n"
                
                # Try with string matching on the timestamp field
                date_str_prefix = f"{year}-{month:02d}-{day:02d}"
                
                try:
                    # Use regex to match the date string prefix
                    cursor = collection.find({
                        "timestamp": {"$regex": f"^{date_str_prefix}"}
                    }).sort("timestamp", 1)
                    
                    async for doc in cursor:
                        try:
                            # For string timestamps
                            if isinstance(doc.get("timestamp"), str):
                                timestamp = doc.get("timestamp").split(".")[0]  # Remove milliseconds
                            else:
                                # For datetime objects
                                timestamp = doc.get("timestamp").strftime("%Y-%m-%d %H:%M:%S")
                                
                            level = doc.get("level", "INFO")
                            source = doc.get("source", "unknown")
                            message = doc.get("message", "")
                            
                            log_line = f"{timestamp} - {level} - {source} - {message}"
                            logs.append(log_line)
                        except Exception as e:
                            logs.append(f"Error formatting log entry: {str(e)}")
                except Exception as e:
                    debug_output += f"Error in alternative query: {str(e)}\n{traceback.format_exc()}\n"
            
            # If still no logs, add debug info
            if not logs:
                # Get all logs to see what's available
                debug_output += "No logs found using either method. Getting sample logs to debug...\n"
                
                try:
                    # Get a few recent logs to debug
                    cursor = collection.find().sort("timestamp", -1).limit(5)
                    
                    sample_logs = []
                    async for doc in cursor:
                        sample_logs.append(str(doc))
                    
                    if sample_logs:
                        debug_output += "Sample logs in database:\n"
                        for sample in sample_logs:
                            debug_output += f"{sample}\n"
                    else:
                        debug_output += "No logs found in database at all.\n"
                except Exception as e:
                    debug_output += f"Error retrieving sample logs: {str(e)}\n"
            
            # Combine logs or return debug info
            if logs:
                return "\n".join(logs)
            else:
                return debug_output
                
        except Exception as e:
            return f"Error retrieving logs: {str(e)}\n{traceback.format_exc()}"