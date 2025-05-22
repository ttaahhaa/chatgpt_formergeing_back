"""
Document management routes: upload, list, delete, and sharing.
"""
import os
import tempfile
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import (
    get_current_user, check_permission, get_document_loader,
    get_vector_store, get_document_repo, get_embedding_repo, get_user_repo
)
from app.utils.jwt_utils import TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(check_permission("documents:upload")),
    document_loader = Depends(get_document_loader),
    vector_store = Depends(get_vector_store)
):
    """Upload a document to the system."""
    try:
        logger.info("Uploading file: %s", file.filename)

        # Save uploaded file to a temp path using the original filename
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.filename)

        with open(temp_path, "wb") as f:
            contents = await file.read()
            f.write(contents)

        # Load document using your loader
        loaded = document_loader.load(temp_path)

        # Flatten the document dict for MongoDB
        document = {
            "id": f"doc_{uuid.uuid4()}",
            "filename": file.filename,
            "extension": loaded.get("extension") or os.path.splitext(file.filename)[1].lower(),
            "content": loaded.get("content", ""),
            "metadata": loaded.get("metadata", {}),
            "owner_id": current_user.user_id,  # Set document owner
            "created_at": datetime.utcnow()
        }
        
        # Add to MongoDB via vector store
        success = await vector_store.async_store.add_document(document)

        # Clean up temp file
        os.unlink(temp_path)

        if success:
            logger.info("Successfully uploaded %s", file.filename)
            return {"message": f"Successfully uploaded {file.filename}"}
        else:
            logger.error("Failed to add document to database: %s", file.filename)
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to add document to database"}
            )

    except ValueError as e:
        logger.error("Invalid document format: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid document format: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except OSError as e:
        logger.error("File operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"File operation error: {str(e)}"}
        )

@router.get("/documents")
async def get_documents(
    current_user: TokenData = Depends(check_permission("documents:view")),
    document_repo = Depends(get_document_repo)
):
    """Get all documents in the system."""
    try:
        # Get documents owned by or shared with this user
        documents = await document_repo.find_accessible(current_user.user_id)
        
        docs = []
        for doc in documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            docs.append(doc)
        
        return {"documents": docs}
    
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid data format: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Invalid data format: {str(e)}"}
        )


@router.post("/documents/share")
async def share_document(
    document_id: str = Form(...),
    share_with_user_id: str = Form(...),
    current_user: TokenData = Depends(check_permission("documents:share")),
    document_repo = Depends(get_document_repo),
    user_repo = Depends(get_user_repo)
):
    """Share a document with another user."""
    try:
        # Check if document exists
        document = await document_repo.find_by_id(document_id)
        
        if not document:
            return JSONResponse(
                status_code=404,
                content={"error": f"Document not found: {document_id}"}
            )
        
        # Check ownership
        owner_id = document["owner_id"] if isinstance(document, dict) else document.owner_id
        if owner_id != current_user.user_id:
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to share this document"}
            )
        
        # Check if target user exists
        target_user = await user_repo.find_by_id(share_with_user_id)
        
        if not target_user:
            return JSONResponse(
                status_code=404,
                content={"error": f"User not found: {share_with_user_id}"}
            )
        
        # Share document
        success = await document_repo.share_document(document_id, share_with_user_id)
        
        if success:
            logger.info("Shared document %s with user %s", document_id, share_with_user_id)
            return {"message": "Document shared successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to share document"}
            )
    
    except (ValueError, AttributeError) as e:
        logger.error("Invalid document or user data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid document or user data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

@router.post("/documents/unshare")
async def unshare_document(
    document_id: str = Form(...),
    user_id: str = Form(...),
    current_user: TokenData = Depends(check_permission("documents:share")),
    document_repo = Depends(get_document_repo)
):
    """Remove a user's access to a shared document."""
    try:
        # Check if document exists
        document = await document_repo.find_by_id(document_id)
        
        if not document:
            return JSONResponse(
                status_code=404,
                content={"error": f"Document not found: {document_id}"}
            )
        
        # Check ownership
        owner_id = document["owner_id"] if isinstance(document, dict) else document.owner_id
        if owner_id != current_user.user_id:
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to modify sharing for this document"}
            )
        
        # Unshare document
        success = await document_repo.unshare_document(document_id, user_id)
        
        if success:
            logger.info("Removed sharing for document %s from user %s", document_id, user_id)
            return {"message": "Document sharing removed successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to remove document sharing"}
            )
    
    except (ValueError, AttributeError) as e:
        logger.error("Invalid document or user data: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid document or user data: {str(e)}"}
        )
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )

"""
/delete_document - Deletes a single specific document by ID
/clear_documents - Clears all documents owned by the current user
/clear_all_documents - Clears all documents in the system (admin only)
"""

@router.post("/delete_document")
async def delete_document(
    document_id: str = Form(...),
    current_user: TokenData = Depends(check_permission("documents:delete")),
    document_repo = Depends(get_document_repo),
    embedding_repo = Depends(get_embedding_repo)
):
    """Delete a document from the system."""
    try:
        # Check if document exists
        document = await document_repo.find_by_id(document_id)
        
        if not document:
            return JSONResponse(
                status_code=404,
                content={"error": f"Document not found: {document_id}"}
            )
        
        # Check ownership if user_id provided
        owner_id = document["owner_id"] if isinstance(document, dict) else document.owner_id
        if owner_id and owner_id != current_user.user_id:
            return JSONResponse(
                status_code=403,
                content={"error": "You don't have permission to delete this document"}
            )
        
        # Delete embedding first
        await embedding_repo.delete_by_document_id(document_id)
        
        # Delete document
        success = await document_repo.delete(document_id)
        
        if success:
            logger.info("Deleted document: %s", document_id)
            return {"message": "Document deleted successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to delete document"}
            )
    
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid document ID: %s", str(e))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid document ID: {str(e)}"}
        )


@router.post("/clear_documents")
async def clear_documents(
    current_user: TokenData = Depends(check_permission("documents:delete")),
    document_repo = Depends(get_document_repo),
    embedding_repo = Depends(get_embedding_repo)
):
    """Clear all documents owned by the current user."""
    try:
        # Get all documents owned by the current user
        documents = await document_repo.find({"owner_id": current_user.user_id})
        
        if not documents:
            return {"message": "No documents found to clear"}
            
        # Delete embeddings and documents for each document
        deleted_count = 0
        for doc in documents:
            doc_id = doc["id"] if isinstance(doc, dict) else doc.id
            
            # Delete embedding first
            await embedding_repo.delete_by_document_id(doc_id)
            
            # Delete document
            success = await document_repo.delete(doc_id)
            if success:
                deleted_count += 1
        
        if deleted_count > 0:
            logger.info("User %s cleared %d documents", current_user.user_id, deleted_count)
            return {"message": f"Successfully cleared {deleted_count} documents"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to clear documents"}
            )
    
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Invalid operation error: {str(e)}"}
        )

@router.post("/clear_all_documents")
async def clear_all_documents(
    current_user: TokenData = Depends(check_permission("admin:manage")),
    vector_store = Depends(get_vector_store)
):
    """Clear all documents from the system. Admin only."""
    try:
        # Use the vector store's clear method
        success = await vector_store.async_store.clear()
        
        if success:
            logger.info("Admin %s cleared all documents from the system", current_user.user_id)
            return {"message": "Successfully cleared all documents"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to clear documents"}
            )
    
    except (ConnectionError, RuntimeError) as e:
        logger.error("Database operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Database operation error: {str(e)}"}
        )
    except (ValueError, AttributeError) as e:
        logger.error("Invalid operation error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"error": f"Invalid operation error: {str(e)}"}
        )