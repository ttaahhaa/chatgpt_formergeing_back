"""
Modern sidebar functionality for Document QA Assistant.
"""

import streamlit as st
from datetime import datetime

from app.ui.utils.components import init_components
from app.ui.utils.conversation import start_new_conversation, load_conversation, load_conversations

def sidebar():
    """Sidebar content with modern UI"""
    components = init_components()
    
    # Add all CSS styling in one place for sidebar adjustments
    st.markdown("""
    <style>
    /* Sidebar width adjustment */
    [data-testid="stSidebar"] {
        width: 220px !important;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        width: 220px !important;
    }
    
    /* Main content adjustment */
    .main .block-container {
        padding-left: 20px;
        padding-right: 20px;
        max-width: calc(100% - 220px);
    }
    
    /* New conversation button styling */
    .new-conversation-btn {
        margin: 5px 0 15px 0 !important;
    }
    
    .new-conversation-btn button {
        background-color: #7267EF !important;
        color: white !important;
        font-weight: bold !important;
        text-align: center !important;
    }
    
    /* Custom conversation item styling */
    .conversation-item {
        padding: 4px 8px;
        background-color: transparent;
        border: none;
        text-align: left;
        color: #333;
        font-weight: normal;
        margin: 1px 0;
        border-radius: 4px;
        cursor: pointer;
        width: 100%;
        display: block;
        line-height: 1.2;
        font-size: 14px;
    }
    
    /* Force text alignment for button content */
    [data-testid="stButton"] > button > div {
        text-align: left !important;
        width: 100% !important;
    }

    /* Target even deeper if needed */
    [data-testid="stButton"] > button > div > p {
        text-align: left !important;
    }
                
    .conversation-item:hover {
        background-color: #f1f0fe;
        border-left: 3px solid #7267EF;
    }
    
    /* Section headers */
    .sidebar-section-title {
        font-weight: bold;
        color: #7267EF;
        margin-top: 16px;
        margin-bottom: 6px;
        font-size: 14px;
        padding-left: 4px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Conversations section
    st.sidebar.markdown("<div class='sidebar-section-title'>Conversations</div>", unsafe_allow_html=True)
    
    # New conversation button with custom class
    with st.sidebar:
        st.markdown('<div class="new-conversation-btn">', unsafe_allow_html=True)
        if st.button("➕ New Conversation", use_container_width=True):
            start_new_conversation()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Make sure conversations are loaded
    if 'conversations' not in st.session_state:
        st.session_state.conversations = load_conversations()
    
    # Show saved conversations with list-style UI
    if st.session_state.conversations:
        # Sort conversations by last updated time (newest first)
        sorted_convs = sorted(
            st.session_state.conversations.items(),
            key=lambda x: datetime.strptime(x[1]["last_updated"], "%Y-%m-%d %H:%M:%S") if isinstance(x[1]["last_updated"], str) else x[1]["last_updated"],
            reverse=True
        )
        
        # Get current conversation ID
        current_conv_id = st.session_state.get('conversation_id', '')
        
        # Just use normal buttons with plain text - no HTML
        for i, (conv_id, conv_data) in enumerate(sorted_convs):
            preview = conv_data['preview']
            # Truncate preview if too long
            if len(preview) > 30:
                preview = preview[:30] + "..."
            
            if st.sidebar.button(
                preview, 
                key=f"conv_{conv_id}",
                use_container_width=True
            ):
                load_conversation(conv_id)
                st.rerun()
    else:
        st.sidebar.markdown("""
        <div style="color: #666; font-size: 13px; padding: 5px 10px;">
            No previous conversations.
        </div>
        """, unsafe_allow_html=True)