"""
General Knowledge tab for Document QA Assistant.
Handles general questions using the LLM's built-in knowledge.
"""

import streamlit as st
import time
from datetime import datetime

from app.ui.utils.components import init_components

def general_knowledge_tab():
    """General Knowledge tab content - for questions not related to documents."""
    # Initialize components
    components = init_components()
    
    st.header("General Knowledge")
    st.markdown(
        """
        Ask general questions that don't require document context. 
        This tab uses the LLM's built-in knowledge to answer your questions.
        """
    )
    
    # Initialize chat history for this tab if it doesn't exist
    if 'general_chat_history' not in st.session_state:
        st.session_state.general_chat_history = []
    
    # Display chat history
    for message in st.session_state.general_chat_history:
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        else:
            st.chat_message("assistant").write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything..."):
        # Display user message
        st.chat_message("user").write(prompt)
        
        # Save user message
        st.session_state.general_chat_history.append({
            "role": "user", 
            "content": prompt,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # Process with LLM directly (no RAG)
        llm_chain = components["llm_chain"]
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # Simulate stream of response with a cursor
            message_placeholder.markdown("▌")
            time.sleep(0.5)
            
            try:
                # Generate response without document retrieval
                # Get just the conversation context without including document context
                conversation_context = [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in st.session_state.general_chat_history[:-1]  # Exclude the current message
                ]
                
                # Special system prompt to inform the LLM it should use its general knowledge
                system_message = {
                    "role": "system",
                    "content": "You are a helpful assistant answering questions based on your general knowledge. "
                               "You do not have access to any specific documents for this question."
                }
                
                # Insert system message at the beginning
                conversation_context.insert(0, system_message)
                
                # Generate response
                response = llm_chain.generate_response(prompt, conversation_context)
                
                # Simulate typing
                for i in range(len(response)):
                    full_response += response[i]
                    if i % 3 == 0:  # Update every few characters for performance
                        time.sleep(0.005)
                        # Add a blinking cursor to simulate typing
                        message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                
                # Save assistant message
                st.session_state.general_chat_history.append({
                    "role": "assistant", 
                    "content": full_response,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
            except Exception as e:
                error_message = f"Error: {str(e)}"
                message_placeholder.markdown(error_message)
                # Save error message
                st.session_state.general_chat_history.append({
                    "role": "assistant", 
                    "content": error_message,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
    
    # Show disclaimer
    st.info(
        "This tab uses the LLM's built-in knowledge rather than your documents. "
        "Responses depend on the local model's training data and capabilities, "
        "and may not always be up-to-date or accurate."
    )
    
    # Add clear button
    if st.button("Clear General Knowledge Conversation"):
        st.session_state.general_chat_history = []
        st.rerun()