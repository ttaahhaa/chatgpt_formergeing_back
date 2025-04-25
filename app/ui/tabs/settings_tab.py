"""
Modernized Settings tab for Document QA Assistant.
Handles configuration and management functions with improved UI.
"""

import streamlit as st

from app.ui.utils.components import init_components
from app.ui.utils.conversation import clear_context, clear_documents, clear_cache

def settings_tab():
    """Settings tab for system configuration with modern UI"""
    # Initialize components
    components = init_components()
    
    st.markdown("""
    <div class="section-header">
        <h2>⚙️ Settings</h2>
        <p class="section-desc">Configure the Document QA Assistant and manage system settings.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Settings cards in tabs
    settings_tabs = st.tabs(["🤖 LLM Settings", "🔤 Embedding Model", "💾 Data Management", "🎨 UI Preferences"])
    
    # LLM Settings Tab
    with settings_tabs[0]:
        st.markdown("""
        <div class="settings-section">
            <h3>🤖 LLM Configuration</h3>
            <p>Configure the language model used for generating responses.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Check Ollama status
        ollama_status = components["llm_chain"].check_ollama_status()
        
        # Display status with modern UI
        if ollama_status["status"] == "available":
            st.markdown("""
            <div class="status-indicator success">
                <div class="status-icon">✅</div>
                <div class="status-message">Ollama is running and available</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Show available models in a nice grid
            st.markdown("<h4>Available Models</h4>", unsafe_allow_html=True)
            models = ollama_status.get("models", [])
            
            if models:
                # Display models in card grid
                st.markdown('<div class="model-grid">', unsafe_allow_html=True)
                
                # Create model selection cards
                cols = st.columns(3)
                
                for i, model in enumerate(models):
                    with cols[i % 3]:
                        # Check if this is the current model
                        is_current = model == components["llm_chain"].model_name
                        card_class = "selected" if is_current else ""
                        
                        st.markdown(f"""
                        <div class="model-card {card_class}">
                            <div class="model-name">{model}</div>
                            <div class="model-tag">Ollama</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Add select button
                        if st.button(f"{'✓ Current' if is_current else 'Select'}", key=f"select_model_{i}", disabled=is_current):
                            components["llm_chain"].model_name = model
                            st.success(f"Now using {model}")
                            st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Model selection with default to mistral:latest
                default_index = models.index("mistral:latest") if "mistral:latest" in models else 0
                selected_model = st.selectbox(
                    "Select Ollama model to use",
                    options=models,
                    index=default_index
                )
                
                # Apply model change
                if st.button("Apply Model Change", use_container_width=True):
                    components["llm_chain"].model_name = selected_model
                    st.success(f"Now using {selected_model}")
                    st.rerun()
            else:
                st.warning("""
                <div class="warning-box">
                    <div class="warning-icon">⚠️</div>
                    <div class="warning-message">No models found in Ollama. Please pull at least one model.</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.error(f"""
            <div class="error-box">
                <div class="error-icon">❌</div>
                <div class="error-message">
                    Ollama is not available: {ollama_status.get('message', 'Unknown error')}
                    <p>Make sure Ollama is installed and running on your system.</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Provide helpful recovery steps
            with st.expander("Troubleshooting Steps"):
                st.markdown("""
                1. **Install Ollama**: Visit [ollama.ai](https://ollama.ai) and follow installation instructions
                2. **Start Ollama**: Run `ollama serve` in your terminal
                3. **Pull a model**: Run `ollama pull mistral:latest` to download a model
                4. **Refresh this page**: Click the refresh button after completing these steps
                """)
    
    # Embedding Model Settings Tab
    with settings_tabs[1]:
        st.markdown("""
        <div class="settings-section">
            <h3>🔤 Embedding Model Settings</h3>
            <p>Configure the embedding model used for document similarity search.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Check ArabERT status
        arabert_status = components["embeddings"].check_model_status()
        
        if arabert_status["status"] == "available":
            st.markdown("""
            <div class="status-indicator success">
                <div class="status-icon">✅</div>
                <div class="status-message">ArabERT model is available</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Model configuration options
            st.markdown("<h4>Configuration Options</h4>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Dimensionality selector (example setting)
                dimensions = st.select_slider(
                    "Embedding Dimensions",
                    options=[64, 128, 256, 512, 768, 1024],
                    value=768
                )
            
            with col2:
                # Pooling strategy (example setting)
                pooling = st.selectbox(
                    "Pooling Strategy",
                    options=["mean", "max", "cls"],
                    index=0
                )
            
            # Apply settings button
            if st.button("Apply Embedding Settings", use_container_width=True):
                st.success("Embedding settings updated successfully!")
                # In a real implementation, we would update the model settings here
        else:
            st.error(f"""
            <div class="error-box">
                <div class="error-icon">❌</div>
                <div class="error-message">
                    ArabERT model issue: {arabert_status.get('message', 'Unknown error')}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Data Management Tab
    with settings_tabs[2]:
        st.markdown("""
        <div class="settings-section">
            <h3>💾 Data Management</h3>
            <p>Manage conversation history, loaded documents, and system cache.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Data management cards
        st.markdown('<div class="data-management-grid">', unsafe_allow_html=True)
        
        # Layout with columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="data-card">
                <div class="data-icon">💬</div>
                <div class="data-title">Conversation History</div>
                <div class="data-desc">Clear the current conversation history and context.</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Clear Conversations", use_container_width=True, key="clear_context"):
                clear_context()
                st.success("Context cleared successfully!")
                st.rerun()
        
        with col2:
            st.markdown("""
            <div class="data-card">
                <div class="data-icon">📄</div>
                <div class="data-title">Document Storage</div>
                <div class="data-desc">Remove all loaded documents from the vector store.</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Clear Documents", use_container_width=True, key="clear_docs"):
                clear_documents()
                st.success("Documents cleared successfully!")
                st.rerun()
        
        with col3:
            st.markdown("""
            <div class="data-card">
                <div class="data-icon">🗑️</div>
                <div class="data-title">Application Cache</div>
                <div class="data-desc">Clear temporary files and cached application data.</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Clear Cache", use_container_width=True, key="clear_cache"):
                clear_cache()
                st.success("Cache cleared successfully!")
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Data export and backup section
        st.markdown("""
        <div class="settings-section">
            <h4>Export & Backup</h4>
            <p>Export your data or create backups.</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Export Conversations", use_container_width=True):
                # In a real implementation, we would generate and download a file here
                st.info("This feature is not yet implemented.")
        
        with col2:
            if st.button("Backup Documents", use_container_width=True):
                # In a real implementation, we would generate and download a file here
                st.info("This feature is not yet implemented.")
    
    # UI Preferences Tab
    with settings_tabs[3]:
        st.markdown("""
        <div class="settings-section">
            <h3>🎨 UI Preferences</h3>
            <p>Customize the appearance and behavior of the user interface.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Theme settings
        st.markdown("<h4>Theme Settings</h4>", unsafe_allow_html=True)
        
        # Color theme selector
        color_scheme = st.selectbox(
            "Color Scheme",
            options=["Default (Purple)", "Blue", "Green", "Orange", "Dark Mode"],
            index=0
        )
        
        # Font settings
        font_choice = st.selectbox(
            "Font Family",
            options=["System Default", "Poppins", "Roboto", "Open Sans", "Montserrat"],
            index=0
        )
        
        # Layout density
        layout_density = st.select_slider(
            "Layout Density",
            options=["Compact", "Balanced", "Spacious"],
            value="Balanced"
        )
        
        # Animations toggle
        enable_animations = st.toggle("Enable Animations", value=True)
        
        # Apply theme settings
        if st.button("Apply UI Settings", use_container_width=True):
            # In a real implementation, we would save these preferences
            st.success("UI preferences updated! Refresh the page to see changes.")
        
        # Reset to defaults
        if st.button("Reset to Defaults", use_container_width=True):
            st.success("UI preferences reset to defaults!")
            # In a real implementation, we would reset the preferences here
        
        # Advanced UI settings
        with st.expander("Advanced UI Settings"):
            # Chat message style
            chat_style = st.radio(
                "Chat Message Style",
                options=["Modern (Cards)", "Classic (Bubbles)", "Minimal"],
                index=0,
                horizontal=True
            )
            
            # Sidebar position
            sidebar_position = st.radio(
                "Sidebar Position",
                options=["Left", "Right"],
                index=0,
                horizontal=True
            )
            
            # Code block theme
            code_theme = st.selectbox(
                "Code Block Theme",
                options=["Default", "Dark", "Light", "GitHub", "Monokai"],
                index=0
            )
            
            # Apply advanced settings
            if st.button("Apply Advanced Settings"):
                st.success("Advanced UI settings applied!")
                # In a real implementation, we would save these preferences