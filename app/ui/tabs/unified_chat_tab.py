"""
Unified Chat tab for Document QA Assistant.
Combines document-based QA and general knowledge capabilities.
"""

import streamlit as st
import time
from datetime import datetime

from app.ui.utils.components import init_components
from app.ui.utils.conversation import init_chat_history, save_message

def unified_chat_tab():
    """Unified interface that combines document-based QA and general knowledge"""
    # Initialize components
    components = init_components()
    
    # Initialize chat history
    init_chat_history()
    
    st.header("Chat Assistant")
    st.markdown(
        """
        Ask questions about your documents or any general knowledge questions.
        The system will automatically use your documents when relevant, or fall back
        to general knowledge when needed.
        """
    )
    
    # Display mode selection (optional)
    mode = st.radio(
        "Knowledge Source:",
        ["Auto (Recommended)", "Documents Only", "General Knowledge Only"],
        horizontal=True
    )
    
    # Show current mode explanation
    if mode == "Auto (Recommended)":
        st.info("The system will try to answer using your documents first, then fall back to general knowledge if needed.")
    elif mode == "Documents Only":
        st.info("The system will only use your uploaded documents to answer questions.")
    else:  # General Knowledge Only
        st.info("The system will use its built-in knowledge without referring to your documents.")
    
    # Display chat history
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        else:
            st.chat_message("assistant").write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question..."):
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
                # Check document store and mode setting
                documents = vector_store.get_documents()
                use_documents = (mode != "General Knowledge Only") and documents
                use_general = (mode != "Documents Only")
                
                # Initialize response variables
                response = ""
                sources = []
                
                if use_documents:
                    # Get relevant documents if any
                    relevant_docs = vector_store.query(prompt, top_k=3)
                    
                    # Check if we have relevant documents with good scores
                    has_relevant_docs = False
                    for doc in relevant_docs:
                        if doc.get("score", 0) > 0.3:  # Threshold for relevance
                            has_relevant_docs = True
                            break
                    
                    if has_relevant_docs:
                        # Generate response with documents
                        response_data = llm_chain.query_with_sources(prompt, relevant_docs)
                        response = response_data["response"]
                        sources = response_data["sources"]
                    elif use_general:
                        # No relevant documents found, use general knowledge
                        message_placeholder.markdown("No relevant documents found. Using general knowledge...")
                        time.sleep(1)
                        
                        # Prepare conversation context for general knowledge
                        conversation_context = [
                            {"role": msg["role"], "content": msg["content"]}
                            for msg in st.session_state.chat_history[:-1]  # Exclude the current message
                        ]
                        
                        # Add system message for general knowledge
                        system_message = {
                            "role": "system",
                            "content": "You are a helpful assistant answering questions based on your general knowledge. "
                                      "The user has not uploaded relevant documents for this question."
                        }
                        
                        conversation_context.insert(0, system_message)
                        
                        # Generate general knowledge response
                        response = llm_chain.generate_response(prompt, conversation_context)
                        sources = []  # No sources for general knowledge
                    else:
                        # No relevant documents and not allowed to use general knowledge
                        response = "I couldn't find relevant information in your documents to answer this question. " \
                                  "Please upload relevant documents or allow me to use general knowledge."
                elif use_general:
                    # Documents not available or not to be used, use general knowledge
                    # Prepare conversation context for general knowledge
                    conversation_context = [
                        {"role": msg["role"], "content": msg["content"]}
                        for msg in st.session_state.chat_history[:-1]  # Exclude the current message
                    ]
                    
                    # Add system message for general knowledge
                    system_message = {
                        "role": "system",
                        "content": "You are a helpful assistant answering questions based on your general knowledge. "
                                  "You do not have access to any specific documents for this question."
                    }
                    
                    conversation_context.insert(0, system_message)
                    
                    # Generate general knowledge response
                    response = llm_chain.generate_response(prompt, conversation_context)
                    sources = []  # No sources for general knowledge
                else:
                    # No documents and not allowed to use general knowledge
                    response = "Document-only mode is selected, but no documents are uploaded or found relevant. " \
                              "Please upload documents or change the mode to allow general knowledge answers."
                
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
                
                # For general knowledge, add disclaimer
                if not sources and use_general:
                    full_response += "\n\n_This response is based on the assistant's general knowledge, not your documents._"
                
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
    if st.button("Clear Chat History"):
        st.session_state.chat_history = []
        if 'conversation_context' in st.session_state:
            st.session_state.conversation_context = []
        st.rerun()