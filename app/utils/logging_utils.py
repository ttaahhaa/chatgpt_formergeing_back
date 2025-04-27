"""
Utility module for logging configuration with explicit date handling.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
import time
import sys

def setup_logging(log_file=None, log_level="INFO", app_name=None):
    """Set up logging configuration with explicit today's date handling.
    
    Args:
        log_file: Path to the log file, if None, a default path will be used
        log_level: Logging level
        app_name: Application name prefix for the log file
    """
    # Get base directory for logs
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    logs_dir = os.path.join(base_dir, "logs")
    
    # Create logs directory if it doesn't exist
    os.makedirs(logs_dir, exist_ok=True)
    
    # Force getting today's date in the correct format
    today = datetime.now().strftime("%Y%m%d")
    
    # If app_name is not provided, try to determine it from the current script
    if app_name is None:
        # Try to determine if we're running in streamlit or regular python
        if 'streamlit' in sys.modules:
            app_name = "streamlit"
        else:
            app_name = "app"
    
    # If log file not specified, create a default one with today's date
    if log_file is None:
        log_file = os.path.join(logs_dir, f"{app_name}_{today}.log")
    
    # Print to stdout for debugging
    print(f"Setting up logging to: {log_file}")
    
    # Create a test entry in the log file to verify it's writable
    try:
        with open(log_file, 'a') as f:
            f.write(f"Log initialized at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    except Exception as e:
        print(f"Warning: Could not write to log file {log_file}: {e}")
        # Try a fallback log file in case there's a permission issue
        log_file = os.path.join(logs_dir, f"fallback_{today}.log")
        try:
            with open(log_file, 'a') as f:
                f.write(f"Fallback log initialized at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            print(f"Using fallback log file: {log_file}")
        except Exception as e2:
            print(f"Warning: Could not write to fallback log file: {e2}")
            # Last resort: use a temporary file
            import tempfile
            temp_dir = tempfile.gettempdir()
            log_file = os.path.join(temp_dir, f"{app_name}_{today}.log")
            print(f"Using temporary log file: {log_file}")
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Clear existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
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
            delay=False  # Open the file immediately
        )
        file_handler.setLevel(getattr(logging, log_level))
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Log the file location
        root_logger.info(f"Logging to file: {log_file}")
    except Exception as e:
        # If we can't set up file logging, continue with console logging only
        console_handler.setLevel(logging.DEBUG)  # Set to DEBUG to make sure we see errors
        root_logger.warning(f"Failed to set up file logging: {e}")
        root_logger.warning("Continuing with console logging only")
    
    # Explicitly test logging to verify it works
    root_logger.info(f"Logging initialized at level {log_level} on {today}")
    
    # List all log files in the directory for debugging
    log_files = os.listdir(logs_dir)
    root_logger.info(f"Current log files: {log_files}")
    
    return root_logger