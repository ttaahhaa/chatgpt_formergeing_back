"""
Modernized Documents management tab for Document QA Assistant.
Handles document upload, viewing, and removal with improved UI.
"""

import os
import tempfile
import streamlit as st
import time

from app.ui.utils.components import init_components

def documents_tab():
    """Documents management tab with modern UI"""
    # Initialize components
    components = init_components()
    
    st.markdown("""
    <div class="section-header">
        <h2>📁 Document Management</h2>
        <p class="section-desc">Upload, view, and manage your documents for the QA system.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Document statistics card
    documents = components["vector_store"].get_documents()
    doc_count = len(documents)
    
    st.markdown(f"""
    <div class="stats-card">
        <div class="stat-item">
            <div class="stat-value">{doc_count}</div>
            <div class="stat-label">Documents</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{sum(len(doc.get('content', '')) for doc in documents)}</div>
            <div class="stat-label">Total Characters</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{sum(len(doc.get('content', '').split()) for doc in documents)}</div>
            <div class="stat-label">Total Words</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Upload section with modern UI
    st.markdown("""
    <div class="upload-section">
        <h3>📤 Upload Documents</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Modern file uploader with drag and drop
    uploaded_files = st.file_uploader(
        "Drag and drop files here",
        accept_multiple_files=True,
        type=None,  # Accept all file types
        key="document_uploader"
    )
    
    if uploaded_files:
        # Progress bar for overall upload progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            # Update progress
            progress = (i / len(uploaded_files))
            progress_bar.progress(progress)
            status_text.text(f"Processing file {i+1} of {len(uploaded_files)}: {uploaded_file.name}")
            
            # Process file with spinner
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
            
            # Small pause for UX
            time.sleep(0.2)
        
        # Complete the progress bar
        progress_bar.progress(1.0)
        status_text.text("All files processed successfully!")
        time.sleep(1)
        status_text.empty()
        progress_bar.empty()
        st.success(f"✅ Successfully processed {len(uploaded_files)} files")
    
    # Document List Section
    st.markdown("""
    <div class="documents-section">
        <h3>📋 Loaded Documents</h3>
    </div>
    """, unsafe_allow_html=True)
    
    if not documents:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">📄</div>
            <div class="empty-text">No documents loaded. Upload documents to get started.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Document cards with modern UI using columns
        st.markdown('<div class="document-list">', unsafe_allow_html=True)
        
        # Use columns for document grid layout
        cols = st.columns(3)
        
        for i, doc in enumerate(documents):
            # Filter by search query if provided
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
            
            # Get document icon based on file type
            if file_type.lower() in ['pdf', 'application/pdf']:
                icon = "📕"
            elif file_type.lower() in ['docx', 'doc', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                icon = "📘"
            elif file_type.lower() in ['txt', 'text/plain']:
                icon = "📄"
            elif file_type.lower() in ['csv', 'text/csv']:
                icon = "📊"
            else:
                icon = "📁"
            
            # Display document card in the appropriate column
            with cols[i % 3]:
                st.markdown(f"""
                <div class="document-card">
                    <div class="document-icon">{icon}</div>
                    <div class="document-info">
                        <div class="document-name">{filename}</div>
                        <div class="document-meta">{file_type} • {size_str}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Preview and actions in expandable section
                with st.expander("Preview & Actions"):
                    # Show preview of content
                    content = doc.get("content", "")
                    if len(content) > 1000:
                        content = content[:1000] + "..."
                    st.text_area("Content Preview", content, height=200)
                    
                    # Action buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"🔍 Full View", key=f"view_{i}"):
                            st.session_state.full_view_doc = doc
                            st.rerun()
                    
                    with col2:
                        if st.button(f"🗑️ Remove", key=f"remove_{i}"):
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
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Document actions
        st.markdown("""
        <div class="document-actions">
            <h4>📝 Batch Actions</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Action buttons with modern styling
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear All Documents", use_container_width=True):
                # Create a confirmation dialog
                st.warning("Are you sure you want to remove all documents? This cannot be undone.")
                confirm_col1, confirm_col2 = st.columns(2)
                with confirm_col1:
                    if st.button("✅ Yes, remove all", key="confirm_remove_all"):
                        try:
                            components["vector_store"].clear()
                            st.success("All documents removed successfully")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error removing documents: {str(e)}")
                with confirm_col2:
                    if st.button("❌ Cancel", key="cancel_remove_all"):
                        st.rerun()
    
        
        with col2:
            if st.button("🔄 Refresh Document List", use_container_width=True):
                st.rerun()
        
        # Show document statistics if requested
        if st.session_state.get('show_doc_stats', False):
            st.markdown("""
            <div class="stats-section">
                <h4>📊 Document Statistics</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Document type breakdown
            doc_types = {}
            for doc in documents:
                doc_type = doc.get("metadata", {}).get("type", "unknown")
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            # Create simple chart of document types
            type_data = {
                'labels': list(doc_types.keys()),
                'values': list(doc_types.values())
            }
            
            # Display the stats
            st.bar_chart(type_data)
            
            # Close button
            if st.button("❌ Close Statistics"):
                st.session_state.show_doc_stats = False
                st.rerun()
    
    # Show full document view if requested
    if hasattr(st.session_state, 'full_view_doc') and st.session_state.full_view_doc is not None:
        doc = st.session_state.full_view_doc
        filename = doc.get("filename", "Document")
        
        st.markdown(f"""
        <div class="full-view-header">
            <h3>📄 {filename}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Document metadata
        st.markdown("<div class='metadata-section'>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Type:** {doc.get('metadata', {}).get('type', 'unknown')}")
        with col2:
            size = doc.get("metadata", {}).get("size", 0)
            # Format size
            if size < 1024:
                size_str = f"{size} bytes"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            st.markdown(f"**Size:** {size_str}")
        with col3:
            st.markdown(f"**Date Added:** {doc.get('metadata', {}).get('date_added', 'Unknown')}")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Full content
        st.markdown("<div class='content-section'>", unsafe_allow_html=True)
        st.markdown("**Full Content:**")
        st.text_area("", doc.get("content", ""), height=400)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Close button
        if st.button("← Back to Document List"):
            st.session_state.full_view_doc = None
            st.rerun()