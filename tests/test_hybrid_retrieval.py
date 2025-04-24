"""
Tests for hybrid retrieval functionality.
"""

import unittest
from unittest.mock import patch, MagicMock

from langchain.schema import Document
from app.core.hybrid_retrieval import HybridRetriever
from app.core.vector_store import VectorStore
from app.core.knowledge_graph import KnowledgeGraph

class TestHybridRetrieval(unittest.TestCase):
    """Test cases for hybrid retrieval functionality."""

    def setUp(self):
        """Set up test environment."""
        # Mock dependencies
        self.mock_vector_store = MagicMock(spec=VectorStore)
        self.mock_vector_store.is_empty.return_value = False
        
        self.mock_kg = MagicMock(spec=KnowledgeGraph)
        self.mock_kg.get_statistics.return_value = {"nodes": 10, "edges": 15}
        
        # Create hybrid retriever with mocked dependencies
        self.retriever = HybridRetriever(self.mock_vector_store, self.mock_kg)
        self.retriever.llm = MagicMock()  # Mock LLM
    
    def test_initialization(self):
        """Test initialization of hybrid retriever."""
        self.assertEqual(self.retriever.vector_store, self.mock_vector_store)
        self.assertEqual(self.retriever.knowledge_graph, self.mock_kg)
    
    def test_process_documents(self):
        """Test processing documents."""
        # Setup mocks
        self.mock_vector_store.add_documents.return_value = 10
        self.mock_kg.build_from_documents.return_value = 15
        
        # Create test documents
        docs = [Document(page_content="test content", metadata={})]
        
        # Process documents
        with patch("app.core.hybrid_retrieval.config") as mock_config:
            mock_config.use_hybrid_rag = True
            result = self.retriever.process_documents(docs)
        
        # Assert
        self.assertEqual(result["chunks"], 10)
        self.assertEqual(result["relationships"], 15)
        self.mock_vector_store.add_documents.assert_called_once_with(docs)
        self.mock_kg.build_from_documents.assert_called_once_with(docs)
    
    def test_process_documents_no_hybrid(self):
        """Test processing documents without hybrid RAG."""
        # Setup mocks
        self.mock_vector_store.add_documents.return_value = 10
        
        # Create test documents
        docs = [Document(page_content="test content", metadata={})]
        
        # Process documents
        with patch("app.core.hybrid_retrieval.config") as mock_config:
            mock_config.use_hybrid_rag = False
            result = self.retriever.process_documents(docs)
        
        # Assert
        self.assertEqual(result["chunks"], 10)
        self.assertEqual(result["relationships"], 0)
        self.mock_vector_store.add_documents.assert_called_once_with(docs)
        self.mock_kg.build_from_documents.assert_not_called()
    
    def test_query_vector_store(self):
        """Test querying vector store."""
        # Setup mocks
        self.mock_vector_store.search.return_value = [
            Document(page_content="result1", metadata={"source": "file1.txt"}),
            Document(page_content="result2", metadata={"source": "file2.txt"})
        ]
        self.mock_vector_store.extract_sources.return_value = {"file1.txt", "file2.txt"}
        self.retriever.llm.predict.return_value = "Test response"
        
        # Query vector store
        result = self.retriever.query_vector_store("test query")
        
        # Assert
        self.assertEqual(result, "Test response\n\nSources: file1.txt, file2.txt")
        self.mock_vector_store.search.assert_called_once()
        self.retriever.llm.predict.assert_called_once()
    
    def test_query_vector_store_empty(self):
        """Test querying empty vector store."""
        # Setup mocks
        self.mock_vector_store.is_empty.return_value = True
        
        # Query vector store
        result = self.retriever.query_vector_store("test query")
        
        # Assert
        self.assertEqual(result, "Vector store is empty. Please upload documents first.")
        self.mock_vector_store.search.assert_not_called()
    
    def test_query_knowledge_graph(self):
        """Test querying knowledge graph."""
        # Setup mocks
        self.mock_kg.query.return_value = "KG response"
        
        # Query knowledge graph
        result = self.retriever.query_knowledge_graph("test query")
        
        # Assert
        self.assertEqual(result, "KG response")
        self.mock_kg.query.assert_called_once_with("test query")
    
    def test_hybrid_query(self):
        """Test hybrid query."""
        # Setup mocks
        self.retriever.query_vector_store = MagicMock(return_value="Vector response")
        self.retriever.query_knowledge_graph = MagicMock(return_value="KG response")
        self.retriever.llm.predict.return_value = "Combined response"
        
        # Execute hybrid query
        result = self.retriever.hybrid_query("test query")
        
        # Assert
        self.assertEqual(result, "Combined response")
        self.retriever.query_vector_store.assert_called_once_with("test query")
        self.retriever.query_knowledge_graph.assert_called_once_with("test query")
        self.retriever.llm.predict.assert_called_once()
    
    def test_hybrid_query_kg_empty(self):
        """Test hybrid query with empty knowledge graph response."""
        # Setup mocks
        self.retriever.query_vector_store = MagicMock(return_value="Vector response")
        self.retriever.query_knowledge_graph = MagicMock(return_value="No relevant information found in knowledge graph.")
        
        # Execute hybrid query
        result = self.retriever.hybrid_query("test query")
        
        # Assert
        self.assertEqual(result, "Vector response")
        self.retriever.query_vector_store.assert_called_once_with("test query")
        self.retriever.query_knowledge_graph.assert_called_once_with("test query")
        self.retriever.llm.predict.assert_not_called()
    
    def test_hybrid_query_vector_empty(self):
        """Test hybrid query with empty vector response."""
        # Setup mocks
        self.retriever.query_vector_store = MagicMock(return_value="No relevant information found in the documents.")
        self.retriever.query_knowledge_graph = MagicMock(return_value="KG response")
        
        # Execute hybrid query
        result = self.retriever.hybrid_query("test query")
        
        # Assert
        self.assertEqual(result, "KG response")
        self.retriever.query_vector_store.assert_called_once_with("test query")
        self.retriever.query_knowledge_graph.assert_called_once_with("test query")
        self.retriever.llm.predict.assert_not_called()
    
    def test_hybrid_query_no_llm(self):
        """Test hybrid query with no LLM available."""
        # Setup mocks
        self.retriever.query_vector_store = MagicMock(return_value="Vector response")
        self.retriever.query_knowledge_graph = MagicMock(return_value="KG response")
        self.retriever.llm = None
        self.retriever._initialize_llm = MagicMock(return_value=False)
        
        # Execute hybrid query
        result = self.retriever.hybrid_query("test query")
        
        # Assert
        self.assertEqual(result, "From knowledge graph:\nKG response\n\nFrom vector search:\nVector response")
        self.retriever.query_vector_store.assert_called_once_with("test query")
        self.retriever.query_knowledge_graph.assert_called_once_with("test query")
    
    def test_query_hybrid_enabled(self):
        """Test main query method with hybrid RAG enabled."""
        # Setup mocks
        self.retriever.hybrid_query = MagicMock(return_value="Hybrid response")
        
        # Execute query with hybrid RAG enabled
        with patch("app.core.hybrid_retrieval.config") as mock_config:
            mock_config.use_hybrid_rag = True
            result = self.retriever.query("test query")
        
        # Assert
        self.assertEqual(result, "Hybrid response")
        self.retriever.hybrid_query.assert_called_once_with("test query")
    
    def test_query_hybrid_disabled(self):
        """Test main query method with hybrid RAG disabled."""
        # Setup mocks
        self.retriever.query_vector_store = MagicMock(return_value="Vector response")
        
        # Execute query with hybrid RAG disabled
        with patch("app.core.hybrid_retrieval.config") as mock_config:
            mock_config.use_hybrid_rag = False
            result = self.retriever.query("test query")
        
        # Assert
        self.assertEqual(result, "Vector response")
        self.retriever.query_vector_store.assert_called_once_with("test query")
        
    def test_get_statistics(self):
        """Test getting statistics."""
        # Setup mocks
        self.mock_kg.get_statistics.return_value = {"nodes": 10, "edges": 15}
        self.mock_vector_store.is_empty.return_value = False
        
        # Get statistics
        with patch("app.core.hybrid_retrieval.config") as mock_config:
            mock_config.use_hybrid_rag = True
            mock_config.model_name = "test-model"
            stats = self.retriever.get_statistics()
        
        # Assert
        self.assertEqual(stats["kg_nodes"], 10)
        self.assertEqual(stats["kg_edges"], 15)
        self.assertEqual(stats["vector_store_empty"], False)
        self.assertEqual(stats["hybrid_enabled"], True)
        self.assertEqual(stats["model"], "test-model")

if __name__ == "__main__":
    unittest.main()