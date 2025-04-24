"""
Sidebar functionality for Document QA Assistant.
"""

import streamlit as st
from datetime import datetime

from app.ui.utils.components import init_components
from app.ui.utils.conversation import start_new_conversation, load_conversation

def sidebar():
    """Sidebar content"""
    components = init_components()
    
    st.sidebar.title("Document QA Assistant")
    
    # Conversation management
    st.sidebar.header("Conversations")
    
    # New conversation button
    if st.sidebar.button("➕ New Conversation"):
        start_new_conversation()
        st.rerun()
    
    # Show saved conversations
    if hasattr(st.session_state, 'conversations'):
        if st.session_state.conversations:
            # Sort conversations by last updated time (newest first)
            sorted_convs = sorted(
                st.session_state.conversations.items(),
                key=lambda x: datetime.strptime(x[1]["last_updated"], "%Y-%m-%d %H:%M:%S") if isinstance(x[1]["last_updated"], str) else x[1]["last_updated"],
                reverse=True
            )
            
            # Prepare selectbox options
            conv_ids = [conv_id for conv_id, _ in sorted_convs]
            conv_labels = {
                conv_id: f"{conv_data['preview']} ({conv_data['message_count']} messages, last updated: {conv_data['last_updated']})"
                for conv_id, conv_data in sorted_convs
            }
            
            # Selectbox for previous conversations
            selected_conv_id = st.sidebar.selectbox(
                "Previous conversations:",
                options=conv_ids,
                format_func=lambda cid: conv_labels[cid]
            )
            
            # Button to load selected conversation
            if st.sidebar.button("Load Selected Conversation"):
                load_conversation(selected_conv_id)
                st.rerun()
        else:
            st.sidebar.write("No previous conversations.")
    
    # Status indicators
    st.sidebar.header("System Status")
    
    # Ollama status indicator
    ollama_status = components["llm_chain"].check_ollama_status()
    if ollama_status["status"] == "available":
        st.sidebar.success("✅ Ollama")
    else:
        st.sidebar.error("❌ Ollama")
    
    # ArabERT status indicator
    arabert_status = components["embeddings"].check_model_status()
    if arabert_status["status"] == "available":
        st.sidebar.success("✅ ArabERT")
    else:
        st.sidebar.error("❌ ArabERT")
    
    # Document count
    documents = components["vector_store"].get_documents()
    st.sidebar.write(f"Documents: {len(documents)}")