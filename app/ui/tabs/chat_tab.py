"""
Chat tab for Document QA Assistant.
Handles document-based question answering.
"""

import streamlit as st
import time

from app.ui.utils.components import init_components
from app.ui.utils.conversation import init_chat_history, save_message

def chat_tab():
    """Chat interface tab for document-based QA"""
    # Initialize components
    components = init_components()
    
    # Initialize chat history
    init_chat_history()
    
    st.header("Chat with Your Documents")
    st.markdown(
        """
        Ask questions about your uploaded documents. The system will retrieve 
        relevant information and generate answers based on the document content.
        """
    )
    
    # Display chat history
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        else:
            st.chat_message("assistant").write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Display user message
        st.chat_message("user").write(prompt)
        
        # Save user message
        save_message("user", prompt)
        
        # Process with LLM
        llm_chain = components["llm_chain"]
        vector_store = components["vector_store"]
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # Simulate stream of response with a cursor
            message_placeholder.markdown("▌")
            time.sleep(0.5)
            
            try:
                # Get relevant documents if any
                relevant_docs = vector_store.query(prompt, top_k=3)
                
                # Generate response
                response_data = llm_chain.query_with_sources(prompt, relevant_docs)
                response = response_data["response"]
                sources = response_data["sources"]
                
                # Simulate typing
                for i in range(len(response)):
                    full_response += response[i]
                    if i % 3 == 0:  # Update every few characters for performance
                        time.sleep(0.005)
                        # Add a blinking cursor to simulate typing
                        message_placeholder.markdown(full_response + "▌")
                
                # Add sources if available
                if sources:
                    source_text = "\n\n**Sources:**\n"
                    for i, source in enumerate(sources):
                        doc_name = source.get("document", f"Document {i+1}")
                        relevance = source.get("relevance", 0.0)
                        relevance_percent = int(relevance * 100)
                        source_text += f"- {doc_name} (Relevance: {relevance_percent}%)\n"
                    
                    full_response += source_text
                
                message_placeholder.markdown(full_response)
                
                # Save assistant message
                save_message("assistant", full_response)
                
                # Update conversation context
                if 'conversation_context' not in st.session_state:
                    st.session_state.conversation_context = []
                
                st.session_state.conversation_context.append({"role": "user", "content": prompt})
                st.session_state.conversation_context.append({"role": "assistant", "content": response})
                
            except Exception as e:
                error_message = f"Error: {str(e)}"
                message_placeholder.markdown(error_message)
                # Save error message
                save_message("assistant", error_message)
    
    # Add clear button
    if st.button("Clear Document Chat History"):
        st.session_state.chat_history = []
        if 'conversation_context' in st.session_state:
            st.session_state.conversation_context = []
        st.rerun()