import streamlit as st
import os
import glob
from datetime import datetime
import time
import json
import uuid
import requests
from pathlib import Path
import tempfile
import sys

st.set_page_config(
    page_title="Document QA Assistant",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add project root to Python path to avoid import issues
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import project modules
from app.core.document_loader import DocumentLoader
from app.core.vector_store import VectorStore
from app.core.llm import LLMChain
from app.core.embeddings import Embeddings

# Initialize components
@st.cache_resource
def init_components():
    """Initialize and cache core components"""
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

# Get components
components = init_components()

# Initialize chat history functions
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
    """Save a message to the current conversation history"""
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
    
    conversations_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
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
    """Load all saved conversations"""
    conversations = {}
    
    conversations_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
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
    """Load a specific conversation"""
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
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
    
    # Clear context, chat history, and documents
    clear_context()
    clear_documents()

# Tab functions
def chat_tab():
    """Chat interface tab"""
    # Initialize chat history
    init_chat_history()
    
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

def documents_tab():
    """Documents management tab"""
    st.header("Document Management")
    
    # Upload section
    st.subheader("Upload Documents")
    uploaded_files = st.file_uploader(
        "Upload documents to analyze",
        accept_multiple_files=True,
        type=None  # Accept all file types
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Save file to temp location
            with st.spinner(f"Processing {uploaded_file.name}..."):
                try:
                    # Save to temp file
                    temp_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Process document
                    document = components["document_loader"].load(temp_path)
                    
                    # Check for errors
                    if "error" in document:
                        st.error(f"Error loading {uploaded_file.name}: {document['error']}")
                        continue
                    
                    # Add to vector store
                    components["vector_store"].add_document(document)
                    components["vector_store"].save()
                    
                    st.success(f"Successfully processed {uploaded_file.name}")
                    
                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {str(e)}")
    
    # View documents section
    st.subheader("Loaded Documents")
    documents = components["vector_store"].get_documents()
    
    if not documents:
        st.info("No documents loaded. Upload documents to get started.")
    else:
        for i, doc in enumerate(documents):
            filename = doc.get("filename", f"Document {i+1}")
            file_type = doc.get("metadata", {}).get("type", "unknown")
            file_size = doc.get("metadata", {}).get("size", 0)
            
            # Format size
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            
            # Display document info
            with st.expander(f"{filename} ({file_type}, {size_str})"):
                # Show preview of content
                content = doc.get("content", "")
                if len(content) > 1000:
                    content = content[:1000] + "..."
                st.text_area("Content Preview", content, height=200)
                
                # Option to remove individual document
                if st.button(f"Remove {filename}", key=f"remove_{i}"):
                    try:
                        # Currently we need to rebuild the vector store without this document
                        # This is a temporary solution; in a real system, we would remove just this document
                        new_documents = [d for d in documents if d.get("filename") != filename]
                        components["vector_store"].clear()
                        for d in new_documents:
                            components["vector_store"].add_document(d)
                        components["vector_store"].save()
                        st.success(f"Removed {filename}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error removing document: {str(e)}")

def settings_tab():
    """Settings tab"""
    st.header("Settings")
    
    # LLM settings
    st.subheader("LLM Settings")
    
    # Check Ollama status
    ollama_status = components["llm_chain"].check_ollama_status()
    
    if ollama_status["status"] == "available":
        st.success("✅ Ollama is running")
        
        # Show available models
        st.write("Available models:")
        models = ollama_status.get("models", [])
        if models:
            for model in models:
                st.write(f"- {model}")
            
            # Model selection with default to mistral:latest
            default_index = models.index("mistral:latest") if "mistral:latest" in models else 0
            selected_model = st.selectbox(
                "Select Ollama model to use",
                options=models,
                index=default_index
            )
            
            # Apply model change
            if st.button("Apply Model"):
                components["llm_chain"].model_name = selected_model
                st.success(f"Now using {selected_model}")
        else:
            st.warning("No models found in Ollama")
    else:
        st.error(f"❌ Ollama is not available: {ollama_status.get('message', 'Unknown error')}")
        st.info("Make sure Ollama is installed and running on your system")
    
    # Embedding model settings
    st.subheader("Embedding Model Settings")
    
    # Check ArabERT status
    arabert_status = components["embeddings"].check_model_status()
    
    if arabert_status["status"] == "available":
        st.success("✅ ArabERT model is available")
    else:
        st.error(f"❌ ArabERT model issue: {arabert_status.get('message', 'Unknown error')}")
    
    # Data Management section
    st.subheader("Data Management")
    st.write("Manage conversation history, loaded documents, and system cache below.")
    
    if st.button("Clear Conversation Context"):
        clear_context()
        st.rerun()
    st.write("Clears the current conversation history and context.")
    
    if st.button("Clear Loaded Documents"):
        clear_documents()
        st.rerun()
    st.write("Removes all loaded documents from the vector store.")
    
    if st.button("Clear Application Cache"):
        clear_cache()
        st.rerun()
    st.write("Clears temporary files and cached data.")

def logs_tab():
    """Logs tab"""
    st.header("System Logs")
    
    # Find log files
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
    log_files = glob.glob(os.path.join(log_dir, "*.log"))
    
    if not log_files:
        st.info("No log files found.")
        return
    
    # Sort log files by modification time (newest first)
    log_files = sorted(log_files, key=os.path.getmtime, reverse=True)
    
    # Create dropdown for selecting log file
    selected_log = st.selectbox(
        "Select log file:",
        options=log_files,
        format_func=lambda x: os.path.basename(x)
    )
    
    if selected_log:
        try:
            with open(selected_log, 'r') as f:
                log_content = f.read()
            
            # Show file info
            file_size = os.path.getsize(selected_log)
            mod_time = datetime.fromtimestamp(os.path.getmtime(selected_log))
            
            st.text(f"File: {os.path.basename(selected_log)}")
            st.text(f"Size: {file_size} bytes")
            st.text(f"Last modified: {mod_time}")
            
            # Display log content in a scrollable box
            st.text_area("Log contents:", log_content, height=400)
            
            # Add refresh button
            if st.button("Refresh Log"):
                st.rerun()
                
        except Exception as e:
            st.error(f"Error reading log file: {str(e)}")

def status_tab():
    """System status tab"""
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
    import platform
    
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

# Sidebar
def sidebar():
    """Sidebar content"""
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

# Clear functions
def clear_context():
    """Clear conversation context"""
    if hasattr(st.session_state, 'conversation_context'):
        st.session_state.conversation_context = []
    if hasattr(st.session_state, 'chat_history'):
        st.session_state.chat_history = []
    st.success("Context cleared successfully!")

def clear_documents():
    """Clear loaded documents"""
    try:
        components["vector_store"].clear()
        st.success("Documents cleared successfully!")
    except Exception as e:
        st.error(f"Error clearing documents: {str(e)}")

def clear_cache():
    """Clear system cache"""
    try:
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cache")
        
        # Remove all files in cache directory
        files = glob.glob(os.path.join(cache_dir, "*"))
        for f in files:
            if os.path.isfile(f):
                os.remove(f)
        
        st.success("Cache cleared successfully!")
    except Exception as e:
        st.error(f"Error clearing cache: {str(e)}")

# Main function
def main():
    """Main application entry point"""
    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Chat", "Documents", "Settings", "Logs", "Status"])
    
    with tab1:
        chat_tab()
    
    with tab2:
        documents_tab()
    
    with tab3:
        settings_tab()
    
    with tab4:
        logs_tab()
    
    with tab5:
        status_tab()
    
    # Add sidebar
    sidebar()

# Import missing modules for documents_tab
import tempfile

# Run the application
if __name__ == "__main__":
    main()