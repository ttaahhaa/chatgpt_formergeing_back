# app/core/mongodb_logger.py

import logging
import asyncio
import sys
from datetime import datetime
from typing import Dict, Any

from app.database.repositories.factory import repository_factory

class MongoDBLogHandler(logging.Handler):
    """
    Custom logging handler that stores logs in MongoDB.
    """
    
    def __init__(self, level=logging.WARNING):  # Only store WARNING and above
        super().__init__(level)
        self.buffer = []
        self.buffer_size = 100  # Flush every 100 logs
        self.loop = None

    def emit(self, record):
        try:
            # Skip logs from the logging system itself to prevent recursion
            if record.name.startswith("app.database.repositories.log_repository"):
                return

            message = self.format(record)
            log_entry = {
                "level": record.levelname,
                "message": message,
                "timestamp": datetime.fromtimestamp(record.created),
                "source": record.name,
                "metadata": {
                    "filename": record.filename,
                    "lineno": record.lineno,
                    "funcName": record.funcName,
                    "process": record.process,
                    "thread": record.thread
                }
            }

            self.buffer.append(log_entry)

            if len(self.buffer) >= self.buffer_size:
                self.flush()
        except Exception as e:
            print(f"Error in MongoDB log handler: {str(e)}", file=sys.stderr)

    def flush(self):
        if not self.buffer:
            return

        try:
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)

            buffer_copy = self.buffer.copy()
            self.buffer = []

            if self.loop.is_running():
                asyncio.create_task(self._store_logs(buffer_copy))
            else:
                self.loop.run_until_complete(self._store_logs(buffer_copy))
        except Exception as e:
            print(f"Error flushing MongoDB logs: {str(e)}", file=sys.stderr)

    async def _store_logs(self, logs):
        try:
            log_repo = repository_factory.log_repository

            # Disable logging during MongoDB writes
            logging.disable(logging.CRITICAL)
            for log in logs:
                await log_repo.add_log(
                    level=log["level"],
                    message=log["message"],
                    source=log["source"],
                    metadata=log["metadata"]
                )
        except Exception as e:
            print(f"Error storing logs in MongoDB: {str(e)}", file=sys.stderr)
        finally:
            logging.disable(logging.NOTSET)

    def close(self):
        self.flush()
        super().close()
