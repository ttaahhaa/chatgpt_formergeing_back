"""
Tests for embeddings functionality.
"""

import unittest
from unittest.mock import patch, MagicMock

from app.core.embeddings import (
    get_arabert_embeddings,
    get_multilingual_embeddings,
    get_appropriate_embeddings
)
from app.utils.text_processing import detect_language

class TestEmbeddings(unittest.TestCase):
    """Test cases for embeddings functionality."""

    @patch("app.core.embeddings.HuggingFaceEmbeddings")
    def test_get_arabert_embeddings_success(self, mock_embeddings):
        """Test getting ArabBERT embeddings successfully."""
        # Setup mock
        mock_instance = MagicMock()
        mock_embeddings.return_value = mock_instance
        
        # Execute function
        result = get_arabert_embeddings(hf_token="test_token")
        
        # Assert
        self.assertEqual(result, mock_instance)
        mock_embeddings.assert_called_once()
        # Check that the model name is correct
        args, kwargs = mock_embeddings.call_args
        self.assertEqual(kwargs["model_name"], "aubmindlab/bert-base-arabertv2")
        # Check that the token is used
        self.assertEqual(kwargs["model_kwargs"]["token"], "test_token")
    
    @patch("app.core.embeddings.HuggingFaceEmbeddings")
    def test_get_arabert_embeddings_exception(self, mock_embeddings):
        """Test handling exceptions when getting ArabBERT embeddings."""
        # Setup mock to raise exception
        mock_embeddings.side_effect = Exception("Test exception")
        
        # Execute function
        result = get_arabert_embeddings()
        
        # Assert
        self.assertIsNone(result)
    
    @patch("app.core.embeddings.HuggingFaceEmbeddings")
    def test_get_multilingual_embeddings_success(self, mock_embeddings):
        """Test getting multilingual embeddings successfully."""
        # Setup mock
        mock_instance = MagicMock()
        mock_embeddings.return_value = mock_instance
        
        # Execute function
        result = get_multilingual_embeddings(hf_token="test_token")
        
        # Assert
        self.assertEqual(result, mock_instance)
        mock_embeddings.assert_called_once()
        # Check that the model name is correct
        args, kwargs = mock_embeddings.call_args
        self.assertEqual(kwargs["model_name"], "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
        # Check that the token is used
        self.assertEqual(kwargs["model_kwargs"]["token"], "test_token")
    
    @patch("app.core.embeddings.detect_language")
    @patch("app.core.embeddings.get_arabert_embeddings")
    @patch("app.core.embeddings.get_multilingual_embeddings")
    def test_get_appropriate_embeddings_arabic(self, mock_multi, mock_arabert, mock_detect):
        """Test getting appropriate embeddings for Arabic text."""
        # Setup mocks
        mock_detect.return_value = "ar"
        mock_arabert_instance = MagicMock()
        mock_arabert.return_value = mock_arabert_instance
        
        # Execute function
        result = get_appropriate_embeddings(text_sample="Arabic text sample")
        
        # Assert
        self.assertEqual(result, mock_arabert_instance)
        mock_detect.assert_called_once_with("Arabic text sample")
        mock_arabert.assert_called_once()
        mock_multi.assert_not_called()
    
    @patch("app.core.embeddings.detect_language")
    @patch("app.core.embeddings.get_arabert_embeddings")
    @patch("app.core.embeddings.get_multilingual_embeddings")
    def test_get_appropriate_embeddings_non_arabic(self, mock_multi, mock_arabert, mock_detect):
        """Test getting appropriate embeddings for non-Arabic text."""
        # Setup mocks
        mock_detect.return_value = "en"
        mock_multi_instance = MagicMock()
        mock_multi.return_value = mock_multi_instance
        
        # Execute function
        result = get_appropriate_embeddings(text_sample="English text sample")
        
        # Assert
        self.assertEqual(result, mock_multi_instance)
        mock_detect.assert_called_once_with("English text sample")
        mock_multi.assert_called_once()
        mock_arabert.assert_not_called()
    
    @patch("app.core.embeddings.detect_language")
    @patch("app.core.embeddings.get_arabert_embeddings")
    @patch("app.core.embeddings.get_multilingual_embeddings")
    @patch("app.core.embeddings.HuggingFaceEmbeddings")
    def test_get_appropriate_embeddings_fallback(self, mock_hf, mock_multi, mock_arabert, mock_detect):
        """Test fallback to basic embeddings when others fail."""
        # Setup mocks
        mock_detect.return_value = "ar"
        mock_arabert.return_value = None
        mock_multi.return_value = None
        mock_hf_instance = MagicMock()
        mock_hf.return_value = mock_hf_instance
        
        # Execute function
        result = get_appropriate_embeddings(text_sample="Arabic text sample")
        
        # Assert
        self.assertEqual(result, mock_hf_instance)
        mock_detect.assert_called_once_with("Arabic text sample")
        mock_arabert.assert_called_once()
        mock_multi.assert_called_once()
        mock_hf.assert_called_once()

    def test_detect_language_arabic(self):
        """Test detecting Arabic language."""
        # Arabic text
        text = "مرحبا بالعالم"
        result = detect_language(text)
        self.assertEqual(result, "ar")
    
    def test_detect_language_english(self):
        """Test detecting English language."""
        # English text
        text = "Hello world"
        result = detect_language(text)
        self.assertEqual(result, "en")

if __name__ == "__main__":
    unittest.main()
