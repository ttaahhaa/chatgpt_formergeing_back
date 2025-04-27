"""
Enhanced Logs tab for Document QA Assistant.
Displays system logs with better error handling and improved UI.
"""

import os
import glob
from datetime import datetime
import streamlit as st
import logging

def logs_tab():
    """Enhanced logs tab for system monitoring with robust error handling"""
    st.markdown("""
    <div class="section-header">
        <h2>📝 System Logs</h2>
        <p class="section-desc">Monitor system logs and debug application issues.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Find log directory with more robust path resolution
    try:
        # First try the standard location
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "logs")
        
        # If that doesn't exist, try a fallback
        if not os.path.exists(log_dir):
            # Try to find it relative to the current working directory
            log_dir = os.path.join(os.getcwd(), "logs")
            
            # If still not found, look for it one directory up
            if not os.path.exists(log_dir):
                log_dir = os.path.join(os.path.dirname(os.getcwd()), "logs")
        
        st.write(f"Looking for logs in: {log_dir}")
        
        # Check if log directory exists
        if not os.path.exists(log_dir):
            st.warning(f"Log directory not found. Creating one at: {log_dir}")
            os.makedirs(log_dir, exist_ok=True)
            
            # Create a default log file if none exists
            default_log_path = os.path.join(log_dir, "app.log")
            if not os.path.exists(default_log_path):
                with open(default_log_path, 'w') as f:
                    f.write(f"Log file created on {datetime.now()}\n")
                st.info(f"Created new log file at {default_log_path}")
        
        # Find all log files
        log_files = glob.glob(os.path.join(log_dir, "*.log"))
        
        # If no .log files, try other extensions
        if not log_files:
            log_files = glob.glob(os.path.join(log_dir, "*.*"))
            
            if log_files:
                st.info("No .log files found, but other potential log files were detected.")
            else:
                # Create a test log file
                test_log_path = os.path.join(log_dir, "app_test.log")
                with open(test_log_path, 'w') as f:
                    f.write(f"Test log file created on {datetime.now()}\n")
                st.info(f"Created test log file at {test_log_path}")
                log_files = [test_log_path]
    except Exception as e:
        st.error(f"Error locating log directory: {str(e)}")
        log_files = []
        
        # Try to create a simple log in the current directory as a fallback
        try:
            temp_log_dir = os.path.join(os.getcwd(), "temp_logs")
            os.makedirs(temp_log_dir, exist_ok=True)
            temp_log_path = os.path.join(temp_log_dir, "fallback.log")
            
            with open(temp_log_path, 'w') as f:
                f.write(f"Fallback log created on {datetime.now()}\n")
                f.write(f"Original error: {str(e)}\n")
            
            log_files = [temp_log_path]
            st.info(f"Created a fallback log at {temp_log_path}")
        except Exception as inner_e:
            st.error(f"Could not create fallback log: {str(inner_e)}")
    
    # If we have log files, continue with normal operation
    if log_files:
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
                with open(selected_log["path"], 'r', encoding='utf-8', errors='replace') as f:
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
                
                # Try to debug the issue
                try:
                    st.write("Attempting to debug the issue:")
                    file_exists = os.path.exists(selected_log["path"])
                    st.write(f"File exists: {file_exists}")
                    
                    if file_exists:
                        file_size = os.path.getsize(selected_log["path"])
                        st.write(f"File size: {file_size} bytes")
                        
                        # Try reading with different encoding
                        try:
                            with open(selected_log["path"], 'r', encoding='latin-1') as f:
                                sample = f.read(1000)  # Read just a sample
                            st.write("First 1000 characters (latin-1 encoding):")
                            st.code(sample)
                        except Exception as enc_e:
                            st.write(f"Still failed with latin-1 encoding: {str(enc_e)}")
                            
                            # Try binary mode
                            try:
                                with open(selected_log["path"], 'rb') as f:
                                    binary_sample = f.read(1000)
                                st.write("First 1000 bytes (binary):")
                                st.code(str(binary_sample))
                            except Exception as bin_e:
                                st.write(f"Binary read failed: {str(bin_e)}")
                except Exception as debug_e:
                    st.write(f"Debug attempt failed: {str(debug_e)}")
                    
        # Add ability to create a test log
        with st.expander("Logging Test Tools"):
            st.write("Generate test log entries to verify logging functionality:")
            
            test_logger_name = st.text_input("Logger name", "test.logger")
            test_message = st.text_input("Log message", "This is a test log message")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("Log DEBUG"):
                    test_logger = logging.getLogger(test_logger_name)
                    test_logger.debug(test_message)
                    st.success("DEBUG message logged")
            
            with col2:
                if st.button("Log INFO"):
                    test_logger = logging.getLogger(test_logger_name)
                    test_logger.info(test_message)
                    st.success("INFO message logged")
            
            with col3:
                if st.button("Log WARNING"):
                    test_logger = logging.getLogger(test_logger_name)
                    test_logger.warning(test_message)
                    st.success("WARNING message logged")
            
            with col4:
                if st.button("Log ERROR"):
                    test_logger = logging.getLogger(test_logger_name)
                    test_logger.error(test_message)
                    st.success("ERROR message logged")
            
            # Add button to create a simple test log file
            if st.button("Create Test Log File"):
                try:
                    test_log_path = os.path.join(log_dir, f"test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
                    with open(test_log_path, 'w') as f:
                        f.write(f"Test log file created on {datetime.now()}\n")
                        f.write("DEBUG - This is a debug message\n")
                        f.write("INFO - This is an info message\n")
                        f.write("WARNING - This is a warning message\n")
                        f.write("ERROR - This is an error message\n")
                    
                    st.success(f"Test log file created at {test_log_path}")
                    st.rerun()  # Refresh to show the new file
                except Exception as e:
                    st.error(f"Failed to create test log: {str(e)}")
    else:
        st.warning("No log files found. Use the tools below to create test logs or check your logging configuration.")
        
        # Add simple log creation tool
        with st.expander("Create Test Log"):
            st.write("Create a test log file to verify the log viewer:")
            
            log_filename = st.text_input("Log filename", "test_log.log")
            log_content = st.text_area("Log content", "This is a test log file.\nINFO - Application started.\nWARNING - This is a warning.\nERROR - This is an error.")
            
            if st.button("Create Log File"):
                try:
                    # Determine log directory
                    log_dir_options = [
                        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "logs"),
                        os.path.join(os.getcwd(), "logs")
                    ]
                    
                    log_dir = None
                    for option in log_dir_options:
                        try:
                            os.makedirs(option, exist_ok=True)
                            log_dir = option
                            break
                        except:
                            continue
                    
                    if not log_dir:
                        log_dir = os.path.join(os.getcwd(), "logs")
                        os.makedirs(log_dir, exist_ok=True)
                    
                    log_path = os.path.join(log_dir, log_filename)
                    with open(log_path, 'w') as f:
                        f.write(log_content)
                    
                    st.success(f"Test log file created at {log_path}")
                    st.rerun()  # Refresh to show the new file
                except Exception as e:
                    st.error(f"Failed to create test log: {str(e)}")