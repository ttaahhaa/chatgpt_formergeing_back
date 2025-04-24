"""
Documents management tab for Document QA Assistant.
Handles document upload, viewing, and removal.
"""

import os
import tempfile
import streamlit as st

from app.ui.utils.components import init_components

def documents_tab():
    """Documents management tab"""
    # Initialize components
    components = init_components()
    
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
                        
    # Add clear all documents button
    if documents:
        if st.button("Clear All Documents"):
            try:
                components["vector_store"].clear()
                st.success("All documents removed successfully")
                st.rerun()
            except Exception as e:
                st.error(f"Error removing documents: {str(e)}")