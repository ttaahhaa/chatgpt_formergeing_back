"""
Component initialization utilities for Document QA Assistant.
"""

import streamlit as st
from app.core.document_loader import DocumentLoader
from app.core.vector_store import VectorStore
from app.core.llm import LLMChain
from app.core.embeddings import Embeddings

@st.cache_resource
def init_components():
    """
    Initialize and cache core components.
    
    Returns:
        Dict: Dictionary of initialized components
    """
    document_loader = DocumentLoader()
    vector_store = VectorStore()
    llm_chain = LLMChain()
    embeddings = Embeddings()
    return {
        "document_loader": document_loader,
        "vector_store": vector_store,
        "llm_chain": llm_chain,
        "embeddings": embeddings
    }