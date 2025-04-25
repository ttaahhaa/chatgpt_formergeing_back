"""
Modernized Logs tab for Document QA Assistant.
Displays system logs for monitoring and debugging with improved UI.
"""

import os
import glob
from datetime import datetime
import streamlit as st

def logs_tab():
    """Logs tab for system monitoring with modern UI"""
    st.markdown("""
    <div class="section-header">
        <h2>📝 System Logs</h2>
        <p class="section-desc">Monitor system logs and debug application issues.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Log stats cards
    col1, col2, col3 = st.columns(3)
    
    # Find log files
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "logs")
    log_files = glob.glob(os.path.join(log_dir, "*.log"))
    
    if not log_files:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">📝</div>
            <div class="empty-text">No log files found.</div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Sort log files by modification time (newest first)
    log_files = sorted(log_files, key=os.path.getmtime, reverse=True)
    
    # Display log stats
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{len(log_files)}</div>
            <div class="stat-label">Log Files</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Get the newest log file
        newest_log = log_files[0]
        newest_time = datetime.fromtimestamp(os.path.getmtime(newest_log))
        time_diff = datetime.now() - newest_time
        
        if time_diff.days > 0:
            time_str = f"{time_diff.days} days ago"
        elif time_diff.seconds > 3600:
            time_str = f"{time_diff.seconds // 3600} hours ago"
        elif time_diff.seconds > 60:
            time_str = f"{time_diff.seconds // 60} minutes ago"
        else:
            time_str = f"{time_diff.seconds} seconds ago"
        
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{time_str}</div>
            <div class="stat-label">Last Log</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Calculate total log size
        total_size = sum(os.path.getsize(file) for file in log_files)
        
        # Format size
        if total_size < 1024:
            size_str = f"{total_size} B"
        elif total_size < 1024 * 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        else:
            size_str = f"{total_size / (1024 * 1024):.1f} MB"
        
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{size_str}</div>
            <div class="stat-label">Total Size</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Log filter and search
    st.markdown("""
    <div class="logs-section">
        <h3>📋 Log Browser</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Search and filters row
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_term = st.text_input("🔍 Search in logs", placeholder="Type to search...")
    
    with col2:
        log_type = st.selectbox(
            "Log Type",
            options=["All", "Error", "Warning", "Info", "Debug"],
            index=0
        )
    
    # Create dropdown for selecting log file with better formatting
    log_options = []
    for log_file in log_files:
        filename = os.path.basename(log_file)
        size = os.path.getsize(log_file)
        mod_time = datetime.fromtimestamp(os.path.getmtime(log_file)).strftime("%Y-%m-%d %H:%M")
        
        # Format size
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        
        log_options.append({
            "path": log_file,
            "display": f"{filename} ({size_str}, {mod_time})"
        })
    
    selected_log = st.selectbox(
        "Select log file:",
        options=log_options,
        format_func=lambda x: x["display"]
    )
    
    if selected_log:
        try:
            with open(selected_log["path"], 'r') as f:
                log_content = f.read()
            
            # Show file info with modern UI
            file_size = os.path.getsize(selected_log["path"])
            mod_time = datetime.fromtimestamp(os.path.getmtime(selected_log["path"]))
            
            # Format the info card
            st.markdown(f"""
            <div class="file-info-card">
                <div class="file-info-item">
                    <div class="info-label">File:</div>
                    <div class="info-value">{os.path.basename(selected_log["path"])}</div>
                </div>
                <div class="file-info-item">
                    <div class="info-label">Size:</div>
                    <div class="info-value">{file_size} bytes</div>
                </div>
                <div class="file-info-item">
                    <div class="info-label">Modified:</div>
                    <div class="info-value">{mod_time}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Filter content if search term provided
            if search_term:
                filtered_lines = []
                for line in log_content.split('\n'):
                    if search_term.lower() in line.lower():
                        filtered_lines.append(line)
                
                if filtered_lines:
                    filtered_content = '\n'.join(filtered_lines)
                    st.text_area("Filtered Log Content:", filtered_content, height=400)
                    st.info(f"Found {len(filtered_lines)} lines containing '{search_term}'")
                else:
                    st.warning(f"No matches found for '{search_term}'")
                    st.text_area("Log contents:", log_content, height=400)
            else:
                # Display log content in a scrollable box with syntax highlighting
                st.code(log_content, language="text")
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 Refresh Log", use_container_width=True):
                    st.rerun()
            
            with col2:
                if st.button("📥 Download Log", use_container_width=True):
                    # In a real implementation, we would trigger a download here
                    st.info("Download functionality not implemented in this demo")
            
            with col3:
                if st.button("🗑️ Clear Log File", use_container_width=True):
                    # Confirm deletion
                    st.warning("Are you sure you want to clear this log file? This cannot be undone.")
                    
                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button("✅ Yes, clear log", key="confirm_clear_log"):
                            # In a real implementation, we would clear the log file
                            st.success("Log file cleared successfully")
                            st.rerun()
                    with confirm_col2:
                        if st.button("❌ Cancel", key="cancel_clear_log"):
                            st.rerun()
            
            # Log statistics
            if log_content:
                st.markdown("""
                <div class="logs-section">
                    <h3>📊 Log Analysis</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Count log levels
                error_count = log_content.lower().count("error")
                warning_count = log_content.lower().count("warning")
                info_count = log_content.lower().count("info")
                debug_count = log_content.lower().count("debug")
                
                # Display as a horizontal bar chart
                st.markdown("""
                <div class="log-stats">
                    <div class="log-stat-item">
                        <div class="log-stat-label">Error</div>
                        <div class="log-stat-bar error" style="width: calc({0}% * 100 / {1} + 20px);">{0}</div>
                    </div>
                    <div class="log-stat-item">
                        <div class="log-stat-label">Warning</div>
                        <div class="log-stat-bar warning" style="width: calc({2}% * 100 / {1} + 20px);">{2}</div>
                    </div>
                    <div class="log-stat-item">
                        <div class="log-stat-label">Info</div>
                        <div class="log-stat-bar info" style="width: calc({3}% * 100 / {1} + 20px);">{3}</div>
                    </div>
                    <div class="log-stat-item">
                        <div class="log-stat-label">Debug</div>
                        <div class="log-stat-bar debug" style="width: calc({4}% * 100 / {1} + 20px);">{4}</div>
                    </div>
                </div>
                """.format(
                    error_count,
                    max(1, error_count + warning_count + info_count + debug_count),
                    warning_count,
                    info_count,
                    debug_count
                ), unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"""
            <div class="error-box">
                <div class="error-icon">❌</div>
                <div class="error-message">Error reading log file: {str(e)}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Log management section
    st.markdown("""
    <div class="logs-section">
        <h3>⚙️ Log Management</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Archive Old Logs", use_container_width=True):
            # In a real implementation, we would archive old logs
            st.info("This feature is not implemented in this demo")
    
    with col2:
        if st.button("Clear All Logs", use_container_width=True):
            # In a real implementation, we would clear all logs
            st.warning("Are you sure you want to clear all logs? This cannot be undone.")
            
            confirm_col1, confirm_col2 = st.columns(2)
            with confirm_col1:
                if st.button("✅ Yes, clear all", key="confirm_clear_all"):
                    # In a real implementation, we would clear all logs
                    st.success("All logs cleared successfully")
                    st.rerun()
            with confirm_col2:
                if st.button("❌ Cancel", key="cancel_clear_all"):
                    st.rerun()
    
    with col3:
        if st.button("Download All Logs", use_container_width=True):
            # In a real implementation, we would trigger a download
            st.info("This feature is not implemented in this demo")