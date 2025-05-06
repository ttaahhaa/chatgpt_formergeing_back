# app/database/repositories/log_repository.py

import logging
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timedelta

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
