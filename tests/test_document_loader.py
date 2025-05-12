"""
Tests for document loader functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path
from langchain.schema import Document

from app.core.document_loader import DocumentLoader

class TestDocumentLoader(unittest.TestCase):
    """Test cases for document loader functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_content = b"This is test content."
        self.test_pdf_content = b"%PDF-1.4\nTest PDF content"
        self.test_docx_content = b"PKTest DOCX content"
        
        # Create temporary test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create test files
        self.txt_file = self.temp_path / "test.txt"
        with open(self.txt_file, "wb") as f:
            f.write(self.test_content)
            
        self.pdf_file = self.temp_path / "test.pdf"
        with open(self.pdf_file, "wb") as f:
            f.write(self.test_pdf_content)
        
        self.loader = DocumentLoader()
    
    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()
    
    @patch("app.core.document_loader.load_from_cache")
    @patch("app.core.document_loader.save_to_cache")
    @patch("app.core.document_loader.DocumentLoader._load_file")
    @patch("app.core.document_loader.get_document_hash")
    def test_load_document_new(self, mock_hash, mock_load_file, mock_save_cache, mock_load_cache):
        """Test loading a document that's not in cache."""
        # Setup mocks
        mock_hash.return_value = "test_hash"
        mock_load_cache.return_value = None
        
        test_docs = [Document(page_content="Test content", metadata={"source": "test.txt"})]
        mock_load_file.return_value = test_docs
        
        # Execute function
        result = self.loader.load_document(self.test_content, "test.txt")
        
        # Assert
        self.assertEqual(result, test_docs)
        mock_hash.assert_called_once_with(self.test_content)
        mock_load_cache.assert_called_once_with("test_hash")
        mock_load_file.assert_called_once()
        mock_save_cache.assert_called_once_with("test_hash", test_docs)
    
    @patch("app.core.document_loader.load_from_cache")
    @patch("app.core.document_loader.save_to_cache")
    @patch("app.core.document_loader.DocumentLoader._load_file")
    @patch("app.core.document_loader.get_document_hash")
    def test_load_document_from_cache(self, mock_hash, mock_load_file, mock_save_cache, mock_load_cache):
        """Test loading a document from cache."""
        # Setup mocks
        mock_hash.return_value = "test_hash"
        cached_docs = [Document(page_content="Cached content", metadata={"source": "test.txt"})]
        mock_load_cache.return_value = cached_docs
        
        # Execute function
        result = self.loader.load_document(self.test_content, "test.txt")
        
        # Assert
        self.assertEqual(result, cached_docs)
        mock_hash.assert_called_once_with(self.test_content)
        mock_load_cache.assert_called_once_with("test_hash")
        mock_load_file.assert_not_called()
        mock_save_cache.assert_not_called()
    
    @patch("app.core.document_loader.TextLoader")
    def test_load_file_txt(self, mock_text_loader):
        """Test loading a text file."""
        # Setup mock
        mock_instance = MagicMock()
        mock_text_loader.return_value = mock_instance
        mock_docs = [Document(page_content="Test content")]
        mock_instance.load.return_value = mock_docs
        
        # Execute function
        result = self.loader.load(str(self.txt_file))
        
        # Assert
        self.assertEqual(result["content"], mock_docs[0].page_content)
        mock_text_loader.assert_called_with(str(self.txt_file), encoding="utf-8")
        mock_instance.load.assert_called_once()
    
    def test_process_documents(self):
        """Test processing documents."""
        # Setup test documents
        docs = [
            Document(page_content="Content 1", metadata={}),
            Document(page_content="", metadata={}),  # Empty document
            Document(page_content="Content 2", metadata={})
        ]
        
        # Execute function
        result = self.loader.process_documents(docs)
        
        # Assert
        self.assertEqual(len(result), 2)  # Should filter out the empty document
        self.assertEqual(result[0].page_content, "Content 1")
        self.assertEqual(result[1].page_content, "Content 2")

if __name__ == "__main__":
    unittest.main()
