"""
Simplified Settings tab for Document QA Assistant.
Handles essential configuration without unnecessary complexity.
"""

import streamlit as st

from app.ui.utils.components import init_components
from app.ui.utils.conversation import clear_context, clear_documents, clear_cache

def settings_tab():
    """Simplified settings tab for system configuration"""
    # Initialize components
    components = init_components()
    
    st.markdown("""
    <div class="section-header">
        <h2>⚙️ Settings</h2>
        <p class="section-desc">Configure the Document QA Assistant and manage system settings.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # LLM Settings Section
    st.subheader("🤖 LLM Configuration")
    
    # Check Ollama status
    ollama_status = components["llm_chain"].check_ollama_status()
    
    if ollama_status["status"] == "available":
        st.success("✅ Ollama is running and available")
        
        # Model selection
        models = ollama_status.get("models", [])
        
        if models:
            # Model selection with default to mistral:latest
            default_index = models.index("mistral:latest") if "mistral:latest" in models else 0
            selected_model = st.selectbox(
                "Select Ollama model to use",
                options=models,
                index=default_index
            )
            
            # Apply model change
            if st.button("Apply Model Change"):
                components["llm_chain"].model_name = selected_model
                st.success(f"Now using {selected_model}")
                st.rerun()
        else:
            st.warning("No models found in Ollama. Please pull at least one model.")
    else:
        st.error(f"Ollama is not available: {ollama_status.get('message', 'Unknown error')}")
        
        # Provide helpful recovery steps
        with st.expander("Troubleshooting Steps"):
            st.markdown("""
            1. **Install Ollama**: Visit [ollama.ai](https://ollama.ai) and follow installation instructions
            2. **Start Ollama**: Run `ollama serve` in your terminal
            3. **Pull a model**: Run `ollama pull mistral:latest` to download a model
            4. **Refresh this page**: Click the refresh button after completing these steps
            """)
    
    # Data Management Section
    st.subheader("💾 Data Management")
    
    # Data management with simple columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Clear Conversations", use_container_width=True):
            clear_context()
            st.success("Context cleared successfully!")
            st.rerun()
        st.caption("Remove conversation history")
    
    with col2:
        if st.button("Clear Documents", use_container_width=True):
            clear_documents()
            st.success("Documents cleared successfully!")
            st.rerun()
        st.caption("Remove loaded documents")
    
    with col3:
        if st.button("Clear Cache", use_container_width=True):
            clear_cache()
            st.success("Cache cleared successfully!")
            st.rerun()
        st.caption("Clear temporary files")
    
    # Advanced Settings (optional expandable section)
    with st.expander("Advanced Settings"):
        st.markdown("### Embeddings Settings")
        
        # Check embedding model status
        arabert_status = components["embeddings"].check_model_status()
        
        if arabert_status["status"] == "available":
            st.success("✅ Embedding model is available")
            
            # Basic embedding settings if needed
            embedding_dim = st.select_slider(
                "Embedding Dimensions",
                options=[128, 256, 384, 512, 768],
                value=384
            )
            
            if st.button("Update Embedding Settings"):
                st.success("Settings updated")
                # In a real app, we would update the settings here
        else:
            st.error(f"Embedding model issue: {arabert_status.get('message', 'Unknown error')}")