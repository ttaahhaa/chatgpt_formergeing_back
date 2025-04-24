"""
Tests for knowledge graph functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
import networkx as nx
import json

from langchain.schema import Document
from app.core.knowledge_graph import KnowledgeGraph

class TestKnowledgeGraph(unittest.TestCase):
    """Test cases for knowledge graph functionality."""

    def setUp(self):
        """Set up test environment."""
        self.kg = KnowledgeGraph()
        
        # Sample Python code for testing
        self.sample_code = """
import numpy as np
import pandas as pd

class DataProcessor:
    def __init__(self, data):
        self.data = data
        
    def process(self):
        return self.data.mean()
        
def load_data(file_path):
    return pd.read_csv(file_path)
"""
        
        # Sample markdown for testing
        self.sample_markdown = """
# Project Documentation

## Introduction
This is a project introduction.

### Goals
This section describes goals.

## Installation
Follow these steps to install.
"""
    
    def test_initialization(self):
        """Test initialization of knowledge graph."""
        self.assertIsInstance(self.kg.graph, nx.DiGraph)
        self.assertEqual(self.kg.graph.number_of_nodes(), 0)
        self.assertEqual(self.kg.graph.number_of_edges(), 0)
        self.assertIsNone(self.kg.llm)
    
    def test_clear(self):
        """Test clearing the knowledge graph."""
        # Add some nodes and edges
        self.kg.graph.add_node("node1")
        self.kg.graph.add_node("node2")
        self.kg.graph.add_edge("node1", "node2", relation="test")
        
        # Clear the graph
        self.kg.clear()
        
        # Check that the graph is empty
        self.assertEqual(self.kg.graph.number_of_nodes(), 0)
        self.assertEqual(self.kg.graph.number_of_edges(), 0)
    
    def test_extract_code_entities(self):
        """Test extracting entities from code."""
        # Extract entities from sample code
        source_file = "test.py"
        triplets = self.kg._extract_code_entities(self.sample_code, source_file)
        
        # Check that the expected entities and relationships are found
        self.assertGreater(len(triplets), 0)
        
        # Find specific expected triplets
        import_numpy = False
        import_pandas = False
        class_def = False
        function_def = False
        
        for triplet in triplets:
            if (triplet["entity1"] == source_file and 
                triplet["relation"] == "imports" and 
                triplet["entity2"] == "numpy"):
                import_numpy = True
            
            if (triplet["entity1"] == source_file and 
                triplet["relation"] == "imports" and 
                triplet["entity2"] == "pandas"):
                import_pandas = True
                
            if (triplet["entity1"] == source_file and 
                triplet["relation"] == "defines class" and 
                triplet["entity2"] == "DataProcessor"):
                class_def = True
                
            if (triplet["entity1"] == source_file and 
                triplet["relation"] == "defines function" and 
                triplet["entity2"] == "load_data"):
                function_def = True
        
        self.assertTrue(import_numpy)
        self.assertTrue(import_pandas)
        self.assertTrue(class_def)
        self.assertTrue(function_def)
    
    def test_extract_markdown_entities(self):
        """Test extracting entities from markdown."""
        # Extract entities from sample markdown
        source_file = "test.md"
        triplets = self.kg._extract_code_entities(self.sample_markdown, source_file)
        
        # Check that the expected entities and relationships are found
        self.assertGreater(len(triplets), 0)
        
        # Find heading hierarchy relationships
        heading_relationship = False
        
        for triplet in triplets:
            if (triplet["entity1"] == "Introduction" and 
                triplet["relation"] == "contains section" and 
                triplet["entity2"] == "Goals"):
                heading_relationship = True
        
        self.assertTrue(heading_relationship)
    
    @patch("app.core.knowledge_graph.KnowledgeGraph._extract_entities_and_relations")
    def test_build_from_documents(self, mock_extract):
        """Test building knowledge graph from documents."""
        # Setup mock
        mock_extract.return_value = [
            {
                "entity1": "file1.py",
                "relation": "imports",
                "entity2": "numpy",
                "source": "file1.py"
            },
            {
                "entity1": "file1.py",
                "relation": "defines",
                "entity2": "process_data",
                "source": "file1.py"
            }
        ]
        
        # Create test documents
        docs = [
            Document(page_content="content1", metadata={"source": "file1.py"}),
            Document(page_content="content2", metadata={"source": "file2.py"})
        ]
        
        # Build knowledge graph
        result = self.kg.build_from_documents(docs)
        
        # Assert
        self.assertEqual(result, 2)  # Two relationships added
        self.assertEqual(self.kg.graph.number_of_nodes(), 3)  # Three nodes: file1.py, numpy, process_data
        self.assertEqual(self.kg.graph.number_of_edges(), 2)  # Two edges
        
        # Check that the mock was called correctly
        self.assertEqual(mock_extract.call_count, 2)
        mock_extract.assert_any_call("content1", "file1.py")
        mock_extract.assert_any_call("content2", "file2.py")
    
    def test_get_statistics(self):
        """Test getting knowledge graph statistics."""
        # Add some nodes and edges
        self.kg.graph.add_node("node1")
        self.kg.graph.add_node("node2")
        self.kg.graph.add_edge("node1", "node2", relation="test")
        
        # Get statistics
        stats = self.kg.get_statistics()
        
        # Check that the statistics are correct
        self.assertEqual(stats["nodes"], 2)
        self.assertEqual(stats["edges"], 1)
    
    def test_get_node_connections(self):
        """Test getting node connections."""
        # Add some nodes and edges
        self.kg.graph.add_node("node1")
        self.kg.graph.add_node("node2")
        self.kg.graph.add_node("node3")
        self.kg.graph.add_edge("node1", "node2", relation="relation1", source="file1")
        self.kg.graph.add_edge("node3", "node1", relation="relation2", source="file2")
        
        # Get connections for node1
        connections = self.kg.get_node_connections("node1")
        
        # Check that the connections are correct
        self.assertEqual(len(connections["outgoing"]), 1)
        self.assertEqual(connections["outgoing"][0]["target"], "node2")
        self.assertEqual(connections["outgoing"][0]["relation"], "relation1")
        
        self.assertEqual(len(connections["incoming"]), 1)
        self.assertEqual(connections["incoming"][0]["source"], "node3")
        self.assertEqual(connections["incoming"][0]["relation"], "relation2")
    
    def test_get_top_entities(self):
        """Test getting top entities."""
        # Add some nodes and edges
        self.kg.graph.add_node("node1")
        self.kg.graph.add_node("node2")
        self.kg.graph.add_node("node3")
        self.kg.graph.add_edge("node1", "node2")
        self.kg.graph.add_edge("node1", "node3")
        self.kg.graph.add_edge("node2", "node3")
        
        # Get top entities
        top_entities = self.kg.get_top_entities(limit=2)
        
        # Check that the top entities are correct
        self.assertEqual(len(top_entities), 2)
        self.assertEqual(top_entities[0][0], "node1")  # node1 has the most connections
        self.assertEqual(top_entities[0][1], 2)        # node1 has 2 connections
    
    def test_search_entities(self):
        """Test searching for entities."""
        # Add some nodes
        self.kg.graph.add_node("test_node")
        self.kg.graph.add_node("another_node")
        self.kg.graph.add_node("test_another")
        
        # Search for entities
        results = self.kg.search_entities("test")
        
        # Check that the search results are correct
        self.assertEqual(len(results), 2)
        self.assertIn("test_node", results)
        self.assertIn("test_another", results)
        self.assertNotIn("another_node", results)
    
    @patch.object(KnowledgeGraph, "initialize_llm")
    @patch("app.core.knowledge_graph.ChatGroq")
    def test_query_with_llm(self, mock_chatgroq, mock_init_llm):
        """Test querying knowledge graph with LLM."""
        # Setup mocks
        mock_init_llm.return_value = True
        mock_llm = MagicMock()
        mock_chatgroq.return_value = mock_llm
        mock_llm.predict.return_value = "Test response"
        self.kg.llm = mock_llm
        
        # Add some nodes and edges that match the query
        self.kg.graph.add_node("python")
        self.kg.graph.add_node("programming")
        self.kg.graph.add_edge("python", "programming", relation="is a", source="file.txt")
        
        # Query the knowledge graph
        result = self.kg.query("What is python?")
        
        # Check that the LLM was used to generate the response
        self.assertEqual(result, "Test response")
        mock_llm.predict.assert_called_once()
        
        # Check that the call contains the relationship info
        call_args = mock_llm.predict.call_args[0][0]
        self.assertIn("python is a programming", call_args)

if __name__ == "__main__":
    unittest.main()
