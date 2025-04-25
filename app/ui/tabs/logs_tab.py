"""
Simplified Logs tab for Document QA Assistant.
Displays system logs with basic filtering and improved UI.
"""

import os
import glob
from datetime import datetime
import streamlit as st

def logs_tab():
    """Simplified logs tab for system monitoring with clean UI"""
    st.markdown("""
    <div class="section-header">
        <h2>📝 System Logs</h2>
        <p class="section-desc">Monitor system logs and debug application issues.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Find log files
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "logs")
    log_files = glob.glob(os.path.join(log_dir, "*.log"))
    
    if not log_files:
        st.info("No log files found. Application logs will appear here once generated.")
        return
    
    # Sort log files by modification time (newest first)
    log_files = sorted(log_files, key=os.path.getmtime, reverse=True)
    
    # Log stats dashboard
    col1, col2, col3 = st.columns(3)
    
    # Total number of log files
    with col1:
        st.metric("Log Files", len(log_files))
    
    # Last update time
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
    
    with col2:
        st.metric("Last Update", time_str)
    
    # Total log size
    total_size = sum(os.path.getsize(file) for file in log_files)
    if total_size < 1024:
        size_str = f"{total_size} B"
    elif total_size < 1024 * 1024:
        size_str = f"{total_size / 1024:.1f} KB"
    else:
        size_str = f"{total_size / (1024 * 1024):.1f} MB"
    
    with col3:
        st.metric("Total Size", size_str)
    
    # Log viewer section
    st.subheader("Log Viewer")
    
    # Create dropdown for selecting log file
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
        "Select log file to view:",
        options=log_options,
        format_func=lambda x: x["display"]
    )
    
    # Simple search and filter
    filter_col1, filter_col2 = st.columns([3, 1])
    
    with filter_col1:
        search_term = st.text_input("🔍 Search in log", placeholder="Type to search...")
    
    with filter_col2:
        log_level = st.multiselect(
            "Log Levels",
            options=["ERROR", "WARNING", "INFO", "DEBUG"],
            default=["ERROR", "WARNING", "INFO", "DEBUG"]
        )
    
    if selected_log:
        try:
            with open(selected_log["path"], 'r') as f:
                log_content = f.read()
            
            # File info
            st.write(f"**File:** {os.path.basename(selected_log['path'])}")
            st.write(f"**Size:** {os.path.getsize(selected_log['path'])} bytes")
            st.write(f"**Modified:** {datetime.fromtimestamp(os.path.getmtime(selected_log['path']))}")
            
            # Apply filters if provided
            if search_term or log_level:
                filtered_lines = []
                for line in log_content.split('\n'):
                    # Skip empty lines
                    if not line.strip():
                        continue
                    
                    # Check search term
                    term_match = not search_term or search_term.lower() in line.lower()
                    
                    # Check log level
                    level_match = False
                    for level in log_level:
                        if f"[{level}]" in line or f" {level} " in line:
                            level_match = True
                            break
                    
                    # If both filters match, add the line
                    if term_match and level_match:
                        filtered_lines.append(line)
                
                if filtered_lines:
                    filtered_content = '\n'.join(filtered_lines)
                    
                    # Create scrollable area with fixed height
                    st.markdown("""
                    <style>
                    .log-container {
                        max-height: 400px;
                        overflow-y: auto;
                        border: 1px solid #e0e0e0;
                        border-radius: 4px;
                        background-color: #f8f9fa;
                        padding: 10px;
                        font-family: monospace;
                        white-space: pre;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    # Display log content in scrollable container
                    st.markdown(f'<div class="log-container">{filtered_content}</div>', unsafe_allow_html=True)
                    
                    st.success(f"Found {len(filtered_lines)} matching lines")
                else:
                    st.warning("No matching lines found")
                    # Show original content in scrollable container
                    st.markdown("""
                    <style>
                    .log-container {
                        max-height: 400px;
                        overflow-y: auto;
                        border: 1px solid #e0e0e0;
                        border-radius: 4px;
                        background-color: #f8f9fa;
                        padding: 10px;
                        font-family: monospace;
                        white-space: pre;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f'<div class="log-container">{log_content}</div>', unsafe_allow_html=True)
            else:
                # Display log content in scrollable container
                st.markdown("""
                <style>
                .log-container {
                    max-height: 400px;
                    overflow-y: auto;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    background-color: #f8f9fa;
                    padding: 10px;
                    font-family: monospace;
                    white-space: pre;
                }
                </style>
                """, unsafe_allow_html=True)
                
                st.markdown(f'<div class="log-container">{log_content}</div>', unsafe_allow_html=True)
            
            # Action buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Refresh", use_container_width=True):
                    st.rerun()
            
            with col2:
                # Download button using built-in functionality
                st.download_button(
                    label="📥 Download Log",
                    data=log_content,
                    file_name=os.path.basename(selected_log["path"]),
                    mime="text/plain",
                    use_container_width=True
                )
            
            # Count log levels
            error_count = sum(1 for line in log_content.lower().split('\n') if "[error]" in line or " error " in line)
            warning_count = sum(1 for line in log_content.lower().split('\n') if "[warning]" in line or " warning " in line)
            info_count = sum(1 for line in log_content.lower().split('\n') if "[info]" in line or " info " in line)
            debug_count = sum(1 for line in log_content.lower().split('\n') if "[debug]" in line or " debug " in line)
            
            # Show simple stats
            st.subheader("Log Summary")
            stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
            
            with stats_col1:
                st.metric("Errors", error_count)
            
            with stats_col2:
                st.metric("Warnings", warning_count)
            
            with stats_col3:
                st.metric("Info", info_count)
            
            with stats_col4:
                st.metric("Debug", debug_count)
            
        except Exception as e:
            st.error(f"Error reading log file: {str(e)}")
    
    # Log management
    with st.expander("Log Management"):
        st.write("Basic log management options:")
        
        management_col1, management_col2 = st.columns(2)
        
        with management_col1:
            if st.button("Clear Selected Log", use_container_width=True):
                if selected_log:
                    try:
                        with open(selected_log["path"], 'w') as f:
                            f.write(f"Log cleared on {datetime.now()}\n")
                        st.success("Log file cleared successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error clearing log: {str(e)}")
        
        with management_col2:
            if st.button("Download All Logs", use_container_width=True):
                # Create a simple concatenated file of all logs
                all_logs = ""
                for log_file in log_files:
                    try:
                        with open(log_file, 'r') as f:
                            file_content = f.read()
                        
                        filename = os.path.basename(log_file)
                        all_logs += f"\n\n--- {filename} ---\n\n"
                        all_logs += file_content
                    except Exception as e:
                        all_logs += f"\n\nError reading {os.path.basename(log_file)}: {str(e)}\n\n"
                
                # Download button
                st.download_button(
                    label="Download Combined Logs",
                    data=all_logs,
                    file_name="all_logs.txt",
                    mime="text/plain"
                )