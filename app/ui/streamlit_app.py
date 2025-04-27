"""
Modified Streamlit application for Document QA Assistant with explicit logging setup.
"""

import streamlit as st
import sys
from pathlib import Path
import os
import logging
from datetime import datetime

# Add project root to Python path to avoid import issues
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Import updated logging utility first
from app.utils.logging_utils import setup_logging

# Setup logging with proper app name
today = datetime.now().strftime("%Y%m%d")
logs_dir = os.path.join(project_root, "logs")
os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, f"streamlit_{today}.log")

# Initialize logger with explicit app name
logger = setup_logging(log_file=log_file, log_level="INFO", app_name="streamlit")
logger.info("Streamlit application starting")

def load_css():
    # Load main CSS
    css_file = os.path.join(project_root, "app", "ui", "static", "css", "custom.css")
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    # Load logs tab specific CSS
    logs_css_file = os.path.join(project_root, "app", "ui", "static", "css", "logs_tab.css")
    if os.path.exists(logs_css_file):
        with open(logs_css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Set up page configuration
st.set_page_config(
    page_title="Interpol Chat Assistant",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import tab modules
from app.ui.tabs.unified_chat_tab import unified_chat_tab
from app.ui.tabs.documents_tab import documents_tab
from app.ui.tabs.settings_tab import settings_tab
from app.ui.tabs.logs_tab import logs_tab
from app.ui.tabs.status_tab import status_tab

# Import utilities
from app.ui.utils.sidebar import sidebar

def main():
    """Main application entry point"""
    logger.info("Starting Document QA Assistant UI")
    try:
        # Load custom CSS
        load_css()
        logger.info("CSS loaded successfully")
    except Exception as e:
        logger.error(f"Could not load custom CSS: {str(e)}")
        st.warning(f"Could not load custom CSS: {str(e)}")
    
    # Add sidebar
    sidebar()
    
    # Main content container
    with st.container():
        # Create tabs - now with a unified chat tab
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "💬 Chat", "📁 Documents", "⚙️ Settings", "📝 Logs", "📊 Status"
        ])
        
        with tab1:
            logger.info("Rendering Chat tab")
            unified_chat_tab()
        
        with tab2:
            logger.info("Rendering Documents tab")
            documents_tab()
        
        with tab3:
            logger.info("Rendering Settings tab")
            settings_tab()
        
        with tab4:
            logger.info("Rendering Logs tab")
            logs_tab()
        
        with tab5:
            logger.info("Rendering Status tab")
            status_tab()

# Run the application
if __name__ == "__main__":
    logger.info("Launching main function")
    main()