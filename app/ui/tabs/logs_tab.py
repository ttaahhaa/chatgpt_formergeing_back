"""
Logs tab for Document QA Assistant.
Displays system logs for monitoring and debugging.
"""

import os
import glob
from datetime import datetime
import streamlit as st

def logs_tab():
    """Logs tab for system monitoring"""
    st.header("System Logs")
    
    # Find log files
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "logs")
    log_files = glob.glob(os.path.join(log_dir, "*.log"))
    
    if not log_files:
        st.info("No log files found.")
        return
    
    # Sort log files by modification time (newest first)
    log_files = sorted(log_files, key=os.path.getmtime, reverse=True)
    
    # Create dropdown for selecting log file
    selected_log = st.selectbox(
        "Select log file:",
        options=log_files,
        format_func=lambda x: os.path.basename(x)
    )
    
    if selected_log:
        try:
            with open(selected_log, 'r') as f:
                log_content = f.read()
            
            # Show file info
            file_size = os.path.getsize(selected_log)
            mod_time = datetime.fromtimestamp(os.path.getmtime(selected_log))
            
            st.text(f"File: {os.path.basename(selected_log)}")
            st.text(f"Size: {file_size} bytes")
            st.text(f"Last modified: {mod_time}")
            
            # Display log content in a scrollable box
            st.text_area("Log contents:", log_content, height=400)
            
            # Add refresh button
            if st.button("Refresh Log"):
                st.rerun()
                
        except Exception as e:
            st.error(f"Error reading log file: {str(e)}")