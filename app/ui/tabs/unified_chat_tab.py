"""
Modernized Unified Chat tab for Document QA Assistant.
Combines document-based QA and general knowledge capabilities with improved UI.
"""

import streamlit as st
import time
from datetime import datetime

from app.ui.utils.components import init_components
from app.ui.utils.conversation import init_chat_history, save_message

def unified_chat_tab():
    """Unified interface that combines document-based QA and general knowledge with modern UI"""
    # Initialize components
    components = init_components()
    
    # Initialize chat history
    init_chat_history()
    

    
    st.markdown("""
    <div class="chat-header">
        <h2>💬 MOI Chat Assistant</h2>
    </div>
    """, unsafe_allow_html=True)
    
    
    # Mode selection with modern UI
    st.markdown('<div class="mode-selector">', unsafe_allow_html=True)
    mode = st.radio(
        "Knowledge Source:",
        ["Auto (Recommended)", "Documents Only", "General Knowledge Only"],
        horizontal=True,
        key="knowledge_mode"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show current mode explanation with styled info box
    if mode == "Auto (Recommended)":
        st.markdown("""
        <div class="info-box auto-mode">
            <div class="info-icon">ℹ️</div>
            <div class="info-content">
                The system will try to answer using your documents first, then fall back to general knowledge if needed.
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif mode == "Documents Only":
        st.markdown("""
        <div class="info-box doc-mode">
            <div class="info-icon">📄</div>
            <div class="info-content">
                The system will only use your uploaded documents to answer questions.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:  # General Knowledge Only
        st.markdown("""
        <div class="info-box general-mode">
            <div class="info-icon">🧠</div>
            <div class="info-content">
                The system will use its built-in knowledge without referring to your documents.
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Chat container with modern styling
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Display chat history with modern styling
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.chat_message("user", avatar="👤").write(message["content"])
        else:
            st.chat_message("assistant", avatar="🤖").write(message["content"])
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input with modern styling
    if prompt := st.chat_input("Ask a question..."):
        # Display user message
        st.chat_message("user", avatar="👤").write(prompt)
        
        # Save user message
        save_message("user", prompt)
        
        # Process with LLM
        llm_chain = components["llm_chain"]
        vector_store = components["vector_store"]
        
        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            full_response = ""
            
            # Show typing indicator
            message_placeholder.markdown("""
            <div class="typing-indicator">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
            </div>
            """, unsafe_allow_html=True)
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
                        message_placeholder.markdown("""
                        <div class="notification">
                            <div class="notification-icon">🔍</div>
                            <div class="notification-content">No relevant documents found. Using general knowledge...</div>
                        </div>
                        """, unsafe_allow_html=True)
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
                
                # Simulate typing with improved animation
                message_placeholder.markdown('<div class="assistant-response typing">', unsafe_allow_html=True)

                for i in range(len(response)):
                    full_response += response[i]
                    if i % 5 == 0:  # Update every few characters for performance
                        time.sleep(0.005)
                        # Use plain text update without the cursor character that could break HTML
                        message_placeholder.write(full_response)
                
                # Add sources if available with modern styling
                if sources:
                    source_text = '<div class="sources-section">'
                    source_text += '<h4>Sources:</h4><ul class="sources-list">'
                    
                    for i, source in enumerate(sources):
                        doc_name = source.get("document", f"Document {i+1}")
                        relevance = source.get("relevance", 0.0)
                        relevance_percent = int(relevance * 100)
                        
                        # Style based on relevance
                        if relevance_percent > 70:
                            relevance_class = "high-relevance"
                        elif relevance_percent > 40:
                            relevance_class = "medium-relevance"
                        else:
                            relevance_class = "low-relevance"
                            
                        source_text += f'<li class="{relevance_class}">'
                        source_text += f'<span class="doc-name">{doc_name}</span>'
                        source_text += f'<span class="relevance-meter" style="width:{relevance_percent}%"></span>'
                        source_text += f'<span class="relevance-percent">{relevance_percent}%</span>'
                        source_text += '</li>'
                    
                    source_text += '</ul></div>'
                    full_response += source_text
                
                # Display final response with proper styling
                message_placeholder.markdown(
                    f'<div class="assistant-response">{full_response}</div>', 
                    unsafe_allow_html=True
                )
                
                # Save assistant message
                save_message("assistant", full_response)
                
                # Update conversation context
                if 'conversation_context' not in st.session_state:
                    st.session_state.conversation_context = []
                
                st.session_state.conversation_context.append({"role": "user", "content": prompt})
                st.session_state.conversation_context.append({"role": "assistant", "content": response})
                
            except Exception as e:
                error_message = f"""
                <div class="error-message">
                    <div class="error-icon">⚠️</div>
                    <div class="error-content">Error: {str(e)}</div>
                </div>
                """
                message_placeholder.markdown(error_message, unsafe_allow_html=True)
                # Save error message
                save_message("assistant", f"Error: {str(e)}")
    