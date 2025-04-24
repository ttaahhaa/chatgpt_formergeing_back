"""
Settings tab for Document QA Assistant.
Handles configuration and management functions.
"""

import streamlit as st

from app.ui.utils.components import init_components
from app.ui.utils.conversation import clear_context, clear_documents, clear_cache

def settings_tab():
    """Settings tab for system configuration"""
    # Initialize components
    components = init_components()
    
    st.header("Settings")
    
    # LLM settings
    st.subheader("LLM Settings")
    
    # Check Ollama status
    ollama_status = components["llm_chain"].check_ollama_status()
    
    if ollama_status["status"] == "available":
        st.success("✅ Ollama is running")
        
        # Show available models
        st.write("Available models:")
        models = ollama_status.get("models", [])
        if models:
            for model in models:
                st.write(f"- {model}")
            
            # Model selection with default to mistral:latest
            default_index = models.index("mistral:latest") if "mistral:latest" in models else 0
            selected_model = st.selectbox(
                "Select Ollama model to use",
                options=models,
                index=default_index
            )
            
            # Apply model change
            if st.button("Apply Model"):
                components["llm_chain"].model_name = selected_model
                st.success(f"Now using {selected_model}")
        else:
            st.warning("No models found in Ollama")
    else:
        st.error(f"❌ Ollama is not available: {ollama_status.get('message', 'Unknown error')}")
        st.info("Make sure Ollama is installed and running on your system")
    
    # Embedding model settings
    st.subheader("Embedding Model Settings")
    
    # Check ArabERT status
    arabert_status = components["embeddings"].check_model_status()
    
    if arabert_status["status"] == "available":
        st.success("✅ ArabERT model is available")
    else:
        st.error(f"❌ ArabERT model issue: {arabert_status.get('message', 'Unknown error')}")
    
    # Data Management section
    st.subheader("Data Management")
    st.write("Manage conversation history, loaded documents, and system cache below.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Clear Conversation Context"):
            clear_context()
            st.success("Context cleared successfully!")
            st.rerun()
        st.write("Clears the current conversation history and context.")
    
    with col2:
        if st.button("Clear Loaded Documents"):
            clear_documents()
            st.rerun()
        st.write("Removes all loaded documents from the vector store.")
    
    with col3:
        if st.button("Clear Application Cache"):
            clear_cache()
            st.rerun()
        st.write("Clears temporary files and cached data.")