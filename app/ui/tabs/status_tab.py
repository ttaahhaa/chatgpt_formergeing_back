"""
Status tab for Document QA Assistant.
Displays system status and statistics.
"""

import streamlit as st
import platform

from app.ui.utils.components import init_components

def status_tab():
    """System status tab displaying system information and statistics"""
    # Initialize components
    components = init_components()
    
    st.header("System Status")
    
    # Check Ollama status
    ollama_status = components["llm_chain"].check_ollama_status()
    
    st.subheader("LLM Status (Ollama)")
    if ollama_status["status"] == "available":
        st.success("✅ Ollama is running")
        
        # Show available models
        models = ollama_status.get("models", [])
        if models:
            st.write("Available models:")
            for model in models:
                st.write(f"- {model}")
        else:
            st.warning("No models found in Ollama")
    else:
        st.error(f"❌ Ollama is not available: {ollama_status.get('message', 'Unknown error')}")
        st.info("Make sure Ollama is installed and running on your system")
    
    # Check ArabERT status
    st.subheader("Embedding Model Status (ArabERT)")
    arabert_status = components["embeddings"].check_model_status()
    
    if arabert_status["status"] == "available":
        st.success("✅ ArabERT model is available")
    else:
        st.error(f"❌ ArabERT model issue: {arabert_status.get('message', 'Unknown error')}")
    
    # Document statistics
    st.subheader("Document Statistics")
    documents = components["vector_store"].get_documents()
    st.write(f"Total documents: {len(documents)}")
    
    # Document types breakdown
    if documents:
        doc_types = {}
        for doc in documents:
            doc_type = doc.get("metadata", {}).get("type", "unknown")
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
        st.write("Document types:")
        for doc_type, count in doc_types.items():
            st.write(f"- {doc_type}: {count}")
    
    # System info
    st.subheader("System Information")
    
    st.write(f"Operating System: {platform.system()} {platform.release()}")
    st.write(f"Python Version: {platform.python_version()}")
    
    # Check for CUDA
    cuda_available = False
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        st.write(f"CUDA Available: {'Yes' if cuda_available else 'No'}")
        if cuda_available:
            st.write(f"CUDA Version: {torch.version.cuda}")
            st.write(f"GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        st.write("PyTorch not installed - GPU status unknown")