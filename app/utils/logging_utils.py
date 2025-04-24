"""
Utility module for logging configuration.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(log_file, log_level="INFO"):
    """Set up logging configuration.
    
    Args:
        log_file: Path to the log file
        log_level: Logging level
    """
    # Create directory for log file if it doesn't exist
    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Clear existing handlers to avoid duplicates
    root_logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    try:
        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5,
            delay=True  # Don't open the file until first log
        )
        file_handler.setLevel(getattr(logging, log_level))
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        # If we can't set up file logging, continue with console logging only
        console_handler.setLevel(logging.DEBUG)  # Set to DEBUG to make sure we see errors
        root_logger.warning(f"Failed to set up file logging: {e}")
        root_logger.warning("Continuing with console logging only")
    
    # Log startup information
    root_logger.info(f"Logging initialized at level {log_level}")
