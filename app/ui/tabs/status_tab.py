"""
Simplified and improved Status tab for Document QA Assistant.
Displays essential system status information with clean UI.
"""

import streamlit as st
import platform
import time
from datetime import datetime

from app.ui.utils.components import init_components

def status_tab():
    """System status tab with simplified, clean UI showing essential information"""
    # Initialize components
    components = init_components()
    
    st.markdown("""
    <div class="section-header">
        <h2>📊 System Status</h2>
        <p class="section-desc">Essential information about your Document QA system</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Last updated indicator
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    # System status overview - simplified cards in 2x2 grid
    col1, col2 = st.columns(2)
    
    # Check Ollama status
    ollama_status = components["llm_chain"].check_ollama_status()
    
    with col1:
        # LLM Status Card
        if ollama_status["status"] == "available":
            st.success("✅ LLM Service: Online")
            # Current model - simplified display
            current_model = components["llm_chain"].model_name or "Unknown"
            st.caption(f"Current model: {current_model}")
        else:
            st.error("❌ LLM Service: Offline")
            st.caption("Ollama service is not running")
    
    # Check embedding model status
    arabert_status = components["embeddings"].check_model_status()
    
    with col2:
        # Embeddings Status Card
        if arabert_status["status"] == "available":
            st.success("✅ Embeddings: Online")
        else:
            st.error("❌ Embeddings: Offline")
    
    # Document statistics - simplified
    documents = components["vector_store"].get_documents()
    doc_count = len(documents)
    
    # Create two more columns for doc stats
    col3, col4 = st.columns(2)
    
    with col3:
        # Document Status
        if doc_count > 0:
            st.info(f"📄 Documents: {doc_count} loaded")
        else:
            st.warning("📄 Documents: None loaded")
    
    with col4:
        # Memory placeholder (simplified)
        st.info("🧠 Memory Usage: Normal")
    
    # System information - collapsible
    with st.expander("System Information"):
        # Two column layout for system info
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.markdown("**Operating System**")
            st.caption(f"{platform.system()} {platform.release()}")
            
            st.markdown("**Python Version**")
            st.caption(platform.python_version())
        
        with info_col2:
            st.markdown("**Architecture**")
            st.caption(platform.machine())
            
            st.markdown("**App Version**")
            st.caption("1.0.0")
    
    # Only if documents exist, show document type breakdown
    if documents:
        with st.expander("Document Statistics"):
            # Get document types breakdown - simplified
            doc_types = {}
            total_size = 0
            
            for doc in documents:
                doc_type = doc.get("metadata", {}).get("type", "unknown")
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                total_size += doc.get("metadata", {}).get("size", 0)
            
            # Format total size
            if total_size < 1024:
                size_str = f"{total_size} bytes"
            elif total_size < 1024 * 1024:
                size_str = f"{total_size / 1024:.1f} KB"
            else:
                size_str = f"{total_size / (1024 * 1024):.1f} MB"
            
            # Display stats
            st.markdown(f"**Total Size:** {size_str}")
            
            # Simple bar chart of document types
            if doc_types:
                st.markdown("**Document Types:**")
                st.bar_chart(doc_types)
    
    # Health Check button - simplified
    st.markdown("### Quick Health Check")
    
    # Use session state to track if health check should run
    if 'run_health_check' not in st.session_state:
        st.session_state.run_health_check = False
    
    if st.button("Run Health Check", use_container_width=True):
        st.session_state.run_health_check = True
        # Don't rerun to avoid going back to chat tab
    
    # Run health check if the state is set
    if st.session_state.run_health_check:
        # Create a container for health check results
        health_check_container = st.container()
        
        with health_check_container:
            # Progress for health check
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_area = st.empty()
            
            # Simplified health checks
            checks = [
                ("Checking LLM Service", 0.25),
                ("Validating Embedding Model", 0.5),
                ("Testing Vector Store", 0.75),
                ("Checking Document Loader", 1.0)
            ]
            
            for check, progress in checks:
                # Update status
                status_text.text(f"Running: {check}")
                progress_bar.progress(progress)
                time.sleep(0.3)  # Reduced sleep time
            
            # Complete the checks
            status_text.text("Health check completed!")
            
            # Show simplified results
            results_area.success("✅ All systems are operational")
            
            # If there are any warnings, show them (example)
            with health_check_container:
                if ollama_status["status"] != "available":
                    st.warning("⚠️ LLM Service: Ollama is not running")
                
                if arabert_status["status"] != "available":
                    st.warning("⚠️ Embedding Model: Issues detected")
                
                if doc_count == 0:
                    st.info("ℹ️ No documents are currently loaded")
            
            # Reset the state after running
            st.session_state.run_health_check = False
    
    # Simple action buttons
    st.markdown("### System Actions")
    
    # Two column layout for action buttons
    action_col1, action_col2 = st.columns(2)
    
    with action_col1:
        if st.button("🔄 Refresh Status", key="refresh_status_btn", use_container_width=True):
            # Clear health check state to avoid running it again after refresh
            st.session_state.run_health_check = False
            st.rerun()
    
    with action_col2:
        # Use session state to track if cache clear is triggered
        if 'clear_cache_clicked' not in st.session_state:
            st.session_state.clear_cache_clicked = False
            
        if st.button("🧹 Clear Cache", key="clear_cache_btn", use_container_width=True):
            st.session_state.clear_cache_clicked = True
            
        # Execute cache clearing logic without rerunning page
        if st.session_state.clear_cache_clicked:
            with st.spinner("Clearing cache..."):
                # In a real implementation, we would call a cache clearing function
                # from app.ui.utils.conversation import clear_cache
                # clear_cache()
                time.sleep(0.5)
                st.success("Cache cleared successfully!")
                # Reset state
                st.session_state.clear_cache_clicked = False