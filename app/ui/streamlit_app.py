"""
Modern Streamlit application for Document QA Assistant.
"""

import streamlit as st
import sys
from pathlib import Path
import os

# Add project root to Python path to avoid import issues
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))


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
    try:
        # Load custom CSS
        load_css()
    except Exception as e:
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
            unified_chat_tab()
        
        with tab2:
            documents_tab()
        
        with tab3:
            settings_tab()
        
        with tab4:
            logs_tab()
        
        with tab5:
            status_tab()
# Run the application
if __name__ == "__main__":
    main()