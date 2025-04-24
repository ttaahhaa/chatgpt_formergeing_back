"""
Conversation management utilities for Document QA Assistant.
"""

import os
import glob
import json
import uuid
import streamlit as st
from datetime import datetime

def init_chat_history():
    """Initialize chat history in session state if it doesn't exist"""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'conversation_id' not in st.session_state:
        st.session_state.conversation_id = str(uuid.uuid4())
    
    if 'conversations' not in st.session_state:
        # Load saved conversations
        st.session_state.conversations = load_conversations()

def save_message(role, content):
    """
    Save a message to the current conversation history
    
    Args:
        role (str): Message role ('user' or 'assistant')
        content (str): Message content
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    message = {
        "role": role,
        "content": content,
        "timestamp": timestamp
    }
    
    st.session_state.chat_history.append(message)
    
    # Save the updated conversation
    save_current_conversation()

def save_current_conversation():
    """Save the current conversation to disk"""
    if len(st.session_state.chat_history) == 0:
        return
    
    conversations_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                     "data", "conversations")
    os.makedirs(conversations_dir, exist_ok=True)
    
    # Create conversation metadata
    first_msg = st.session_state.chat_history[0]["content"]
    preview = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg
    last_timestamp = st.session_state.chat_history[-1]["timestamp"]
    
    conversation_data = {
        "id": st.session_state.conversation_id,
        "messages": st.session_state.chat_history,
        "preview": preview,
        "last_updated": last_timestamp,
        "message_count": len(st.session_state.chat_history)
    }
    
    # Save to file
    file_path = os.path.join(conversations_dir, f"{st.session_state.conversation_id}.json")
    with open(file_path, 'w') as f:
        json.dump(conversation_data, f, indent=2)
    
    # Update conversations list
    st.session_state.conversations[st.session_state.conversation_id] = {
        "preview": preview,
        "last_updated": last_timestamp,
        "message_count": len(st.session_state.chat_history)
    }

def load_conversations():
    """
    Load all saved conversations
    
    Returns:
        dict: Dictionary of conversation data
    """
    conversations = {}
    
    conversations_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                    "data", "conversations")
    
    if not os.path.exists(conversations_dir):
        os.makedirs(conversations_dir, exist_ok=True)
        return conversations
    
    for filename in os.listdir(conversations_dir):
        if filename.endswith('.json'):
            try:
                file_path = os.path.join(conversations_dir, filename)
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                conv_id = data.get("id", filename.replace(".json", ""))
                conversations[conv_id] = {
                    "preview": data.get("preview", "Conversation"),
                    "last_updated": data.get("last_updated", "Unknown"),
                    "message_count": data.get("message_count", 0)
                }
            except Exception as e:
                st.error(f"Error loading conversation {filename}: {str(e)}")
    
    return conversations

def load_conversation(conversation_id):
    """
    Load a specific conversation
    
    Args:
        conversation_id (str): ID of the conversation to load
        
    Returns:
        bool: True if successful, False otherwise
    """
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                            "data", "conversations", f"{conversation_id}.json")
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        st.session_state.conversation_id = conversation_id
        st.session_state.chat_history = data.get("messages", [])
        
        return True
    except Exception as e:
        st.error(f"Error loading conversation: {str(e)}")
        return False

def start_new_conversation():
    """Start a new conversation with a fresh state"""
    # Generate new conversation ID
    st.session_state.conversation_id = str(uuid.uuid4())
    
    # Clear context and chat history
    clear_context()

def clear_context():
    """Clear conversation context"""
    if hasattr(st.session_state, 'conversation_context'):
        st.session_state.conversation_context = []
    if hasattr(st.session_state, 'chat_history'):
        st.session_state.chat_history = []

def clear_documents():
    """Clear loaded documents"""
    try:
        from app.ui.utils.components import init_components
        components = init_components()
        components["vector_store"].clear()
        st.success("Documents cleared successfully!")
    except Exception as e:
        st.error(f"Error clearing documents: {str(e)}")

def clear_cache():
    """Clear system cache"""
    try:
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                "data", "cache")
        
        # Remove all files in cache directory
        files = glob.glob(os.path.join(cache_dir, "*"))
        for f in files:
            if os.path.isfile(f):
                os.remove(f)
        
        st.success("Cache cleared successfully!")
    except Exception as e:
        st.error(f"Error clearing cache: {str(e)}")