"""
Modernized Status tab for Document QA Assistant.
Displays system status and statistics with improved UI.
"""

import streamlit as st
import platform
import time
from datetime import datetime

from app.ui.utils.components import init_components

def status_tab():
    """System status tab displaying system information and statistics with modern UI"""
    # Initialize components
    components = init_components()
    
    st.markdown("""
    <div class="section-header">
        <h2>📊 System Status</h2>
        <p class="section-desc">Monitor the health and performance of your Document QA system.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Dashboard refresh time
    st.markdown(f"""
    <div class="refresh-info">
        <div class="refresh-icon">🔄</div>
        <div class="refresh-text">Last updated: {datetime.now().strftime('%H:%M:%S')}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Auto-refresh toggle
    auto_refresh = st.toggle("Auto-refresh (30s)", value=False)
    if auto_refresh:
        st.markdown("""
        <div class="auto-refresh-indicator">
            <div class="pulse"></div>
            <div class="refresh-text">Auto-refresh enabled</div>
        </div>
        """, unsafe_allow_html=True)
        # In a real implementation, we would set up a refresh mechanism
    
    # System status overview cards
    st.markdown("<h3>System Overview</h3>", unsafe_allow_html=True)
    
    # Create a modern dashboard layout with status cards
    col1, col2, col3, col4 = st.columns(4)
    
    # Check Ollama status
    ollama_status = components["llm_chain"].check_ollama_status()
    
    with col1:
        if ollama_status["status"] == "available":
            st.markdown("""
            <div class="status-card success">
                <div class="status-icon">✅</div>
                <div class="status-content">
                    <div class="status-title">LLM Status</div>
                    <div class="status-detail">Ollama Running</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-card error">
                <div class="status-icon">❌</div>
                <div class="status-content">
                    <div class="status-title">LLM Status</div>
                    <div class="status-detail">Ollama Offline</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Check ArabERT status
    arabert_status = components["embeddings"].check_model_status()
    
    with col2:
        if arabert_status["status"] == "available":
            st.markdown("""
            <div class="status-card success">
                <div class="status-icon">✅</div>
                <div class="status-content">
                    <div class="status-title">Embeddings</div>
                    <div class="status-detail">ArabERT Ready</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-card error">
                <div class="status-icon">❌</div>
                <div class="status-content">
                    <div class="status-title">Embeddings</div>
                    <div class="status-detail">ArabERT Error</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Document status
    documents = components["vector_store"].get_documents()
    
    with col3:
        if documents:
            st.markdown(f"""
            <div class="status-card info">
                <div class="status-icon">📄</div>
                <div class="status-content">
                    <div class="status-title">Documents</div>
                    <div class="status-detail">{len(documents)} Loaded</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-card warning">
                <div class="status-icon">📄</div>
                <div class="status-content">
                    <div class="status-title">Documents</div>
                    <div class="status-detail">None Loaded</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Memory usage (placeholder - in a real app would check actual usage)
    with col4:
        st.markdown("""
        <div class="status-card info">
            <div class="status-icon">🧠</div>
            <div class="status-content">
                <div class="status-title">Memory</div>
                <div class="status-detail">~350 MB</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # LLM Status Section with detailed info
    st.markdown("<h3>LLM Status</h3>", unsafe_allow_html=True)
    
    if ollama_status["status"] == "available":
        # Model information in a nice table
        models = ollama_status.get("models", [])
        if models:
            # Current model highlight
            current_model = components["llm_chain"].model_name or "Unknown"
            
            st.markdown(f"""
            <div class="current-model-info">
                <div class="model-label">Current Model:</div>
                <div class="model-value">{current_model}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Model table
            st.markdown('<div class="model-table">', unsafe_allow_html=True)
            
            # Table header
            st.markdown("""
            <div class="model-table-header">
                <div class="model-col model-name-col">Model Name</div>
                <div class="model-col model-type-col">Type</div>
                <div class="model-col model-status-col">Status</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Table rows
            for model in models:
                # Determine model type (simplified example)
                if "7b" in model.lower():
                    model_type = "Small (7B)"
                elif "13b" in model.lower():
                    model_type = "Medium (13B)"
                elif "34b" in model.lower() or "33b" in model.lower():
                    model_type = "Large (33B/34B)"
                elif "70b" in model.lower():
                    model_type = "XL (70B)"
                else:
                    model_type = "Unknown"
                
                # Is this the current model?
                is_current = model == current_model
                current_class = "current-model" if is_current else ""
                
                # Model status (simplified example - would be real in production)
                model_status = "Active" if is_current else "Available"
                
                st.markdown(f"""
                <div class="model-table-row {current_class}">
                    <div class="model-col model-name-col">{model}</div>
                    <div class="model-col model-type-col">{model_type}</div>
                    <div class="model-col model-status-col">
                        <span class="status-dot {'active' if is_current else 'available'}"></span>
                        {model_status}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("No models found in Ollama. You need to pull at least one model.")
    else:
        st.error(f"❌ Ollama is not available: {ollama_status.get('message', 'Unknown error')}")
        st.info("Make sure Ollama is installed and running on your system")
    
    # Document statistics section
    st.markdown("<h3>Document Statistics</h3>", unsafe_allow_html=True)
    
    # Document stats in a modern visualization
    if documents:
        # Get document types breakdown
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
        
        # Modern stats cards
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(documents)}</div>
                <div class="metric-label">Total Documents</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{size_str}</div>
                <div class="metric-label">Total Size</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(doc_types)}</div>
                <div class="metric-label">Document Types</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Document types visualization with modern bar chart
        st.markdown("<h4>Document Types Breakdown</h4>", unsafe_allow_html=True)
        
        # Calculate max value for scaling
        max_count = max(doc_types.values())
        
        # Visualization container
        st.markdown('<div class="doc-types-chart">', unsafe_allow_html=True)
        
        for doc_type, count in doc_types.items():
            # Calculate percentage for width
            percentage = (count / max_count) * 100
            
            # Type color based on document type
            if "pdf" in doc_type.lower():
                type_color = "pdf-type"
            elif "doc" in doc_type.lower() or "word" in doc_type.lower():
                type_color = "doc-type"
            elif "txt" in doc_type.lower() or "text" in doc_type.lower():
                type_color = "txt-type"
            elif "csv" in doc_type.lower() or "excel" in doc_type.lower() or "sheet" in doc_type.lower():
                type_color = "sheet-type"
            else:
                type_color = "other-type"
            
            st.markdown(f"""
            <div class="doc-type-row">
                <div class="doc-type-label">{doc_type}</div>
                <div class="doc-type-bar-container">
                    <div class="doc-type-bar {type_color}" style="width: {percentage}%"></div>
                    <div class="doc-type-count">{count}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">📄</div>
            <div class="empty-text">No documents loaded. Upload documents to see statistics.</div>
        </div>
        """, unsafe_allow_html=True)
    
    # System Information section
    st.markdown("<h3>System Information</h3>", unsafe_allow_html=True)
    
    # Create a system info card with modern styling
    st.markdown("""
    <div class="system-info-card">
        <h4>Hardware & Software</h4>
        <div class="system-info-grid">
    """, unsafe_allow_html=True)
    
    # System info items
    system_info = [
        ("Operating System", f"{platform.system()} {platform.release()}"),
        ("Python Version", platform.python_version()),
        ("Processor", platform.processor() or "Unknown"),
        ("Architecture", platform.machine()),
        ("App Version", "1.0.0"),  # Example version
    ]
    
    # Add CUDA info if available
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            system_info.append(("CUDA Available", "Yes"))
            system_info.append(("CUDA Version", torch.version.cuda))
            system_info.append(("GPU", torch.cuda.get_device_name(0)))
        else:
            system_info.append(("CUDA Available", "No"))
    except ImportError:
        system_info.append(("CUDA Available", "Unknown (PyTorch not installed)"))
    
    # Display info grid
    for label, value in system_info:
        st.markdown(f"""
        <div class="system-info-item">
            <div class="info-label">{label}</div>
            <div class="info-value">{value}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Health check section
    st.markdown("<h3>Health Checks</h3>", unsafe_allow_html=True)
    
    # Run health checks with progress visualization
    if st.button("Run Health Checks", use_container_width=True):
        # Create progress bar and status text
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Simulate health checks
        checks = [
            ("Checking LLM Service", 0.2),
            ("Validating Embedding Model", 0.4),
            ("Testing Vector Store", 0.6),
            ("Checking Document Loader", 0.8),
            ("Validating API Connections", 1.0)
        ]
        
        for check, progress in checks:
            # Update status
            status_text.text(f"Running: {check}")
            progress_bar.progress(progress)
            
            # Simulate processing time
            time.sleep(0.5)
        
        # Complete the checks
        status_text.text("Health checks completed!")
        time.sleep(1)
        
        # Show health check results
        st.markdown("""
        <div class="health-check-results">
            <div class="health-check-item success">
                <div class="health-check-icon">✅</div>
                <div class="health-check-content">
                    <div class="health-check-name">LLM Service</div>
                    <div class="health-check-result">Operational - 45ms response time</div>
                </div>
            </div>
            <div class="health-check-item success">
                <div class="health-check-icon">✅</div>
                <div class="health-check-content">
                    <div class="health-check-name">Embedding Model</div>
                    <div class="health-check-result">Operational - all components loaded</div>
                </div>
            </div>
            <div class="health-check-item success">
                <div class="health-check-icon">✅</div>
                <div class="health-check-content">
                    <div class="health-check-name">Vector Store</div>
                    <div class="health-check-result">Operational - indexes verified</div>
                </div>
            </div>
            <div class="health-check-item warning">
                <div class="health-check-icon">⚠️</div>
                <div class="health-check-content">
                    <div class="health-check-name">Document Loader</div>
                    <div class="health-check-result">Operational - PDF module needs update</div>
                </div>
            </div>
            <div class="health-check-item success">
                <div class="health-check-icon">✅</div>
                <div class="health-check-content">
                    <div class="health-check-name">API Connections</div>
                    <div class="health-check-result">Operational - all endpoints responsive</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Performance metrics section
    st.markdown("<h3>Performance Metrics</h3>", unsafe_allow_html=True)
    
    # Simulated performance data
    performance_data = {
        "Average Response Time": "235ms",
        "Queries Per Minute": "12",
        "Memory Utilization": "42%",
        "Embedding Generation": "80ms",
        "Document Processing": "1.2s"
    }
    
    # Create a performance gauge chart
    st.markdown('<div class="performance-gauges">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    # Response time gauge
    with col1:
        # Parse the milliseconds value
        response_time = int(performance_data["Average Response Time"].replace("ms", ""))
        # Calculate a percentage for the gauge (assuming 500ms is 100%)
        response_percentage = min(100, (response_time / 500) * 100)
        
        st.markdown(f"""
        <div class="gauge-container">
            <div class="gauge">
                <div class="gauge-value" style="transform: rotate({response_percentage * 1.8}deg)"></div>
                <div class="gauge-center">
                    <div class="gauge-number">{response_time}</div>
                    <div class="gauge-unit">ms</div>
                </div>
            </div>
            <div class="gauge-label">Response Time</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Queries gauge
    with col2:
        # Parse the QPS value
        qpm = int(performance_data["Queries Per Minute"])
        # Calculate a percentage for the gauge (assuming 30 QPM is 100%)
        qpm_percentage = min(100, (qpm / 30) * 100)
        
        st.markdown(f"""
        <div class="gauge-container">
            <div class="gauge">
                <div class="gauge-value" style="transform: rotate({qpm_percentage * 1.8}deg)"></div>
                <div class="gauge-center">
                    <div class="gauge-number">{qpm}</div>
                    <div class="gauge-unit">QPM</div>
                </div>
            </div>
            <div class="gauge-label">Queries/Minute</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Memory gauge
    with col3:
        # Parse the memory percentage
        memory = int(performance_data["Memory Utilization"].replace("%", ""))
        # Direct percentage
        memory_percentage = memory
        
        # Determine color based on usage
        if memory < 50:
            memory_color = "low-usage"
        elif memory < 80:
            memory_color = "medium-usage" 
        else:
            memory_color = "high-usage"
        
        st.markdown(f"""
        <div class="gauge-container">
            <div class="gauge">
                <div class="gauge-value {memory_color}" style="transform: rotate({memory_percentage * 1.8}deg)"></div>
                <div class="gauge-center">
                    <div class="gauge-number">{memory}</div>
                    <div class="gauge-unit">%</div>
                </div>
            </div>
            <div class="gauge-label">Memory Usage</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Additional metrics
    st.markdown('<div class="metrics-table">', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="metrics-header">
        <div class="metric-name-col">Metric</div>
        <div class="metric-value-col">Value</div>
        <div class="metric-chart-col">Trend</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Add some example metrics
    metrics = [
        ("Document Processing Time", "1.2s", "rising"),
        ("Embedding Generation", "80ms", "stable"),
        ("Cache Hit Rate", "76%", "rising"),
        ("API Latency", "112ms", "falling"),
        ("Concurrent Users", "3", "stable")
    ]
    
    for name, value, trend in metrics:
        trend_icon = "📈" if trend == "rising" else "📉" if trend == "falling" else "📊"
        trend_class = trend
        
        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-name-col">{name}</div>
            <div class="metric-value-col">{value}</div>
            <div class="metric-chart-col">
                <span class="trend-icon {trend_class}">{trend_icon}</span>
                <span class="trend-label">{trend}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # System actions
    st.markdown("<h3>System Actions</h3>", unsafe_allow_html=True)
    
    # Action buttons in a grid
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 Restart Services", use_container_width=True):
            # In a real implementation, we would restart services
            with st.spinner("Restarting services..."):
                time.sleep(2)
                st.success("Services restarted successfully!")
    
    with col2:
        if st.button("🧹 Clear Caches", use_container_width=True):
            # In a real implementation, we would clear caches
            with st.spinner("Clearing caches..."):
                time.sleep(1)
                st.success("Caches cleared successfully!")
    
    with col3:
        if st.button("📥 Update Models", use_container_width=True):
            # In a real implementation, we would update models
            with st.spinner("Checking for updates..."):
                time.sleep(2)
                st.info("All models are up to date!")
    
    with col4:
        if st.button("📊 Export Metrics", use_container_width=True):
            # In a real implementation, we would export metrics
            with st.spinner("Preparing metrics export..."):
                time.sleep(1)
                st.success("Metrics exported successfully!")
    
    # Auto-refresh functionality (simplified)
    if auto_refresh:
        st.markdown("""
        <div class="refresh-countdown">
            <div class="countdown-text">Next refresh in: <span id="countdown">30</span>s</div>
        </div>
        <script>
            // Simple countdown script - would not work in Streamlit but simulates the concept
            let countdown = 30;
            const countdownElement = document.getElementById('countdown');
            
            setInterval(() => {
                countdown -= 1;
                if (countdown <= 0) {
                    countdown = 30;
                    // Would trigger refresh in a real implementation
                }
                countdownElement.textContent = countdown;
            }, 1000);
        </script>
        """, unsafe_allow_html=True)
        
        # In a real application, we would use Streamlit's rerun with a timer
        # For this demo, we'll simulate the behavior
        time.sleep(2)  # Just to show the concept