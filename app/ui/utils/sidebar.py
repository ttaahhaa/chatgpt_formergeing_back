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
        width: 280px !important;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        width: 280px !important;
    }
    
    /* Fix for the sidebar collapse button */
    button[kind="headerNoPadding"] {
        z-index: 999 !important;
        position: relative !important;
    }
    
    [data-testid="stSidebarNav"] {
        z-index: 998 !important; 
        position: relative !important;
    }
    
    /* Main content adjustment */
    .main .block-container {
        padding-left: 20px;
        padding-right: 20px;
        max-width: calc(100% - 280px);
    }
    
    /* New conversation button styling */
    .new-conversation-btn {
        margin: 8px 0 20px 0 !important;
        padding: 0 5px;
    }
    
    .new-conversation-btn button {
        background-color: #7267EF !important;
        color: white !important;
        font-weight: bold !important;
        text-align: center !important;
        padding: 10px 15px !important;
        width: 100%;
    }
    
    /* Custom conversation item styling - table row style */
    .conversation-item {
        padding: 6px 8px;
        background-color: transparent;
        border: none;
        text-align: left;
        color: #333;
        font-weight: normal;
        margin: 1px 0; /* Very small gap */
        border-radius: 0; /* No radius */
        cursor: pointer;
        width: 100%;
        display: block;
        line-height: 1.2;
        font-size: 14px;
        transition: background-color 0.1s ease;
        border-bottom: 1px solid #f0f0f0; /* Light separator like table rows */
    }
    
    /* Force text alignment for button content */
    [data-testid="stButton"] > button {
        width: 100% !important;
        padding: 6px 8px !important;
        margin: 0 !important; /* No margin */
        min-height: 0 !important;
        height: auto !important;
        border-radius: 0 !important; /* No radius */
        border-bottom: 1px solid #f0f0f0; /* Table row separator */
    }
    
    [data-testid="stButton"] > button > div {
        text-align: left !important;
        width: 100% !important;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* Target even deeper if needed */
    [data-testid="stButton"] > button > div > p {
        text-align: left !important;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
                
    .conversation-item:hover, [data-testid="stButton"] > button:hover {
        background-color: #f8f8f8 !important; /* Lighter highlight */
        border-left: 2px solid #7267EF !important;
    }
    
    /* Active conversation styling */
    [data-testid="stButton"].active > button {
        background-color: #f1f0fe !important;
        border-left: 2px solid #7267EF !important;
    }
    
    /* Section headers */
    .sidebar-section-title {
        font-weight: bold;
        color: #7267EF;
        margin-top: 5px; /* Reduced from 20px */
        margin-bottom: 10px;
        font-size: 15px;
        padding-left: 12px;
    }
    
    /* Enhance sidebar content width */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        padding-left: 0;
        padding-right: 0;
        width: 100%;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdown"] {
        padding-left: 10px;
        padding-right: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # No header/title as requested
    
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
        
        # Create a container for table-like styling
        st.sidebar.markdown('<div style="padding: 0; margin: 0;">', unsafe_allow_html=True)
        
        # Generate a table-like list of conversations
        for i, (conv_id, conv_data) in enumerate(sorted_convs):
            preview = conv_data['preview']
            # Truncate preview if too long
            if len(preview) > 32:
                preview = preview[:32] + "..."
            
            # Add date display to make it more informative
            last_updated = conv_data.get('last_updated', '')
            try:
                if isinstance(last_updated, str):
                    date_obj = datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S")
                    date_display = date_obj.strftime("%m/%d")
                else:
                    date_display = ""
            except:
                date_display = ""
                
            # Add active class if this is the current conversation
            button_class = "active" if conv_id == current_conv_id else ""
            
            # Table-row style button
            if st.sidebar.button(
                f"{preview}", 
                key=f"conv_{conv_id}",
                use_container_width=True
            ):
                load_conversation(conv_id)
                st.rerun()
        
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown("""
        <div style="color: #666; font-size: 13px; padding: 10px 15px; background-color: #f8f9fa; border-radius: 4px; margin: 5px 10px;">
            No previous conversations. Start a new one!
        </div>
        """, unsafe_allow_html=True)
    
    # Simplified footer
    st.sidebar.markdown(
        """
        <div style="margin-top: 30px; width: 100%; text-align: center; padding: 5px; color: #666; font-size: 11px; border-top: 1px solid #f0f0f0;">
            <p>v1.0.0</p>
        </div>
        """,
        unsafe_allow_html=True
    )