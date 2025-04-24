"""
Knowledge Graph module for Document QA Assistant.
Provides functionality for building and querying a knowledge graph.
"""

import re
import json
import logging
import networkx as nx
from typing import List, Dict, Any, Optional, Tuple

from langchain.schema import Document
from langchain_groq import ChatGroq

from app.config import config
from app.utils.text_processing import is_code_file

logger = logging.getLogger(__name__)

class KnowledgeGraph:
    """Knowledge Graph for document relationships."""
    
    def __init__(self):
        """Initialize an empty knowledge graph."""
        self.graph = nx.DiGraph()
        self.llm = None
    
    def initialize_llm(self) -> bool:
        """
        Initialize LLM for entity extraction.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not config.groq_api_key:
                logger.warning("No GROQ API key provided. LLM-based extraction will be limited.")
                return False
                
            self.llm = ChatGroq(
                api_key=config.groq_api_key,
                model_name=config.model_name
            )
            logger.info(f"Initialized LLM with model {config.model_name}")
            return True
        except Exception as e:
            logger.error(f"Error initializing LLM: {str(e)}", exc_info=True)
            return False
    
    def clear(self):
        """Clear the knowledge graph."""
        self.graph.clear()
        logger.info("Knowledge graph cleared")
    
    def build_from_documents(self, documents: List[Document]) -> int:
        """
        Build knowledge graph from documents.
        
        Args:
            documents: List of documents to process
            
        Returns:
            Number of relationships (edges) added to the graph
        """
        if not documents:
            return 0
        
        try:
            # Initialize LLM if needed and not already initialized
            if self.llm is None:
                self.initialize_llm()
            
            total_triplets = 0
            
            # Process each document
            for i, doc in enumerate(documents):
                # Extract entities and relations
                source_file = doc.metadata.get("source", "unknown")
                triplets = self._extract_entities_and_relations(doc.page_content, source_file)
                
                # Add to graph
                for triplet in triplets:
                    entity1 = triplet.get("entity1", "").strip()
                    relation = triplet.get("relation", "").strip()
                    entity2 = triplet.get("entity2", "").strip()
                    source = triplet.get("source", "unknown")
                    
                    if entity1 and relation and entity2:
                        # Add nodes if they don't exist
                        if not self.graph.has_node(entity1):
                            self.graph.add_node(entity1)
                        
                        if not self.graph.has_node(entity2):
                            self.graph.add_node(entity2)
                        
                        # Add edge with attributes
                        self.graph.add_edge(entity1, entity2, relation=relation, source=source)
                        total_triplets += 1
            
            # Log statistics
            nodes = self.graph.number_of_nodes()
            edges = self.graph.number_of_edges()
            logger.info(f"Knowledge graph built with {nodes} nodes and {edges} edges")
            
            return total_triplets
        except Exception as e:
            logger.error(f"Error building knowledge graph: {str(e)}", exc_info=True)
            return 0
    
    def _extract_entities_and_relations(self, text: str, source_file: str) -> List[Dict[str, str]]:
        """
        Extract entities and relations from text to build a knowledge graph.
        First tries with regex-based extraction, if results are minimal and LLM available,
        uses LLM as backup.
        
        Args:
            text: Text content to extract from
            source_file: Source file name for reference
            
        Returns:
            List of triplets (entity1, relation, entity2)
        """
        # First use the direct code extraction method
        triplets = self._extract_code_entities(text, source_file)
        
        # If we got a good number of triplets, return them
        if len(triplets) >= 5:
            logger.info(f"Extracted {len(triplets)} relationships using regex-based extraction")
            return triplets
        
        # Otherwise, try using the LLM if available
        if self.llm is not None:
            try:
                # Special prompt for code files
                if is_code_file(text):
                    extraction_prompt = f"""
                    Extract key entities and their relationships from the following code.
                    Focus on classes, functions, methods, imports, and their relationships.
                    Format your response as a JSON array of objects, where each object has:
                    - "entity1": The first entity (class, function, module, etc.)
                    - "relation": The relationship between the entities (imports, defines, calls, etc.)
                    - "entity2": The second entity (class, function, module, etc.)

                    CODE: {text[:4000]}  # Limit size to avoid token limits

                    JSON:
                    """
                else:
                    # General prompt for non-code
                    extraction_prompt = f"""
                    Extract key entities and their relationships from the following text.
                    Format your response as a JSON array of objects, where each object has:
                    - "entity1": The first entity
                    - "relation": The relationship between the entities
                    - "entity2": The second entity

                    Only extract factual, clearly stated relationships. Do not infer or guess.
                    Text: {text[:4000]}  # Limit size to avoid token limits

                    JSON:
                    """
                
                # Get extraction response
                extraction_result = self.llm.predict(extraction_prompt)
                
                # Parse extraction result
                try:
                    # Clean the response to get valid JSON
                    extraction_result = extraction_result.strip()
                    if extraction_result.startswith("```json"):
                        extraction_result = extraction_result.split("```json")[1]
                    if extraction_result.endswith("```"):
                        extraction_result = extraction_result.split("```")[0]
                    
                    # Sometimes there's text before or after the JSON
                    start_idx = extraction_result.find("[")
                    end_idx = extraction_result.rfind("]") + 1
                    if start_idx >= 0 and end_idx > start_idx:
                        extraction_result = extraction_result[start_idx:end_idx]
                    
                    llm_triplets = json.loads(extraction_result)
                    
                    # Add metadata about source
                    for triplet in llm_triplets:
                        triplet["source"] = source_file
                    
                    # Combine with regex results
                    combined_triplets = triplets + llm_triplets
                    
                    logger.info(f"Extracted {len(combined_triplets)} relationships using combined extraction")
                    return combined_triplets
                except json.JSONDecodeError:
                    logger.error(f"Could not parse entity extraction response")
                    logger.debug(f"Raw extraction result: {extraction_result}")
                    return triplets  # Return what we have from regex
            except Exception as e:
                logger.error(f"Error in LLM-based entity extraction: {str(e)}", exc_info=True)
        
        return triplets  # Return what we have from regex
    
    def _extract_code_entities(self, text: str, source_file: str) -> List[Dict[str, str]]:
        """
        Extract code entities and relations directly from code files
        without using LLM to avoid API request issues.
        
        Args:
            text: Code content to analyze
            source_file: Source file name for reference
            
        Returns:
            List of triplets (entity1, relation, entity2)
        """
        triplets = []
        
        # Try to detect if this is code
        if is_code_file(text):
            # Extract imports
            import_pattern = r'(?:from|import)\s+([\w\d_.]+)(?:\s+(?:as|import)\s+([\w\d_]+))?'
            imports = re.findall(import_pattern, text)
            for imp in imports:
                module = imp[0].strip() if imp[0] else ''
                alias = imp[1].strip() if len(imp) > 1 and imp[1] else ''
                
                if module:
                    triplets.append({
                        "entity1": source_file,
                        "relation": "imports",
                        "entity2": module,
                        "source": source_file
                    })
                    
                    if alias:
                        triplets.append({
                            "entity1": module,
                            "relation": "has alias",
                            "entity2": alias,
                            "source": source_file
                        })
            
            # Extract class definitions
            class_pattern = r'class\s+([\w\d_]+)(?:\([^)]*\))?:'
            classes = re.findall(class_pattern, text)
            for cls in classes:
                triplets.append({
                    "entity1": source_file,
                    "relation": "defines class",
                    "entity2": cls,
                    "source": source_file
                })
            
            # Extract function definitions
            func_pattern = r'def\s+([\w\d_]+)\s*\('
            functions = re.findall(func_pattern, text)
            for func in functions:
                if func.startswith('__') and func.endswith('__'):
                    # Special methods
                    triplets.append({
                        "entity1": source_file,
                        "relation": "has special method",
                        "entity2": func,
                        "source": source_file
                    })
                else:
                    triplets.append({
                        "entity1": source_file,
                        "relation": "defines function",
                        "entity2": func,
                        "source": source_file
                    })
            
            # Try to link functions to classes
            # This is a simplified approach - a full parser would be better
            lines = text.split('\n')
            current_class = None
            for line in lines:
                line = line.strip()
                
                # Check for class definition
                class_match = re.search(class_pattern, line)
                if class_match:
                    current_class = class_match.group(1)
                    continue
                    
                # Check for function definition
                if current_class:
                    func_match = re.search(func_pattern, line)
                    if func_match and '    def ' in line:  # Check indentation
                        func_name = func_match.group(1)
                        triplets.append({
                            "entity1": current_class,
                            "relation": "has method",
                            "entity2": func_name,
                            "source": source_file
                        })
        else:
            # For non-code, extract basic entities using regex
            # Extract potential entities (capitalized words, technical terms)
            entity_pattern = r'\b([A-Z][a-zA-Z0-9_]{2,}|[a-zA-Z][a-zA-Z0-9_]{2,}(?:[Mm]odel|[Aa]pi|[Ss]ervice|[Ff]unction|[Cc]lass|API|SDK))\b'
            entities = re.findall(entity_pattern, text)
            
            # Create basic connections between entities and the document
            for entity in entities:
                triplets.append({
                    "entity1": source_file,
                    "relation": "mentions",
                    "entity2": entity,
                    "source": source_file
                })
                
            # Try to extract section headings from Markdown
            if source_file.endswith('.md'):
                heading_pattern = r'^(#{1,6})\s+(.+)$'
                headings = []
                for line in text.split('\n'):
                    heading_match = re.search(heading_pattern, line)
                    if heading_match:
                        level = len(heading_match.group(1))
                        heading = heading_match.group(2).strip()
                        headings.append((level, heading))
                
                # Link headings with hierarchy
                for i in range(len(headings) - 1):
                    curr_level, curr_heading = headings[i]
                    next_level, next_heading = headings[i + 1]
                    
                    if next_level > curr_level:
                        triplets.append({
                            "entity1": curr_heading,
                            "relation": "contains section",
                            "entity2": next_heading,
                            "source": source_file
                        })
        
        return triplets
    
    def query(self, question: str) -> str:
        """
        Query the knowledge graph for relevant information.
        
        Args:
            question: User query
            
        Returns:
            Response based on knowledge graph
        """
        if self.graph.number_of_nodes() == 0:
            return "Knowledge graph is empty. Please upload documents first."
        
        try:
            # Extract entities from question
            # We'll use a simple approach of checking if nodes partially match question terms
            entities = []
            
            # Split question into significant terms
            question_terms = re.findall(r'\b\w{3,}\b', question.lower())
            
            # Find matching nodes
            for node in self.graph.nodes():
                node_lower = node.lower()
                if any(term in node_lower for term in question_terms):
                    entities.append(node)
            
            # If no direct match, try broader matches
            if not entities:
                for node in self.graph.nodes():
                    node_lower = node.lower()
                    # Check if any significant word from the node is in the question
                    node_terms = re.findall(r'\b\w{3,}\b', node_lower)
                    if any(term in question.lower() for term in node_terms):
                        entities.append(node)
            
            # Limit to top 5 most connected entities if we have too many
            if len(entities) > 5:
                entities = sorted(
                    entities,
                    key=lambda x: self.graph.degree(x),
                    reverse=True
                )[:5]
            
            logger.info(f"Extracted entities for KG query: {entities}")
            
            # Get knowledge graph context
            graph_context = []
            
            # Method 1: Direct node matching
            for entity in entities:
                # Get all edges connected to this node
                for successor in self.graph.successors(entity):
                    edge_data = self.graph.get_edge_data(entity, successor)
                    relation = edge_data.get("relation", "is related to")
                    source = edge_data.get("source", "unknown")
                    triplet = f"{entity} {relation} {successor}"
                    graph_context.append(triplet)
                
                for predecessor in self.graph.predecessors(entity):
                    edge_data = self.graph.get_edge_data(predecessor, entity)
                    relation = edge_data.get("relation", "is related to")
                    source = edge_data.get("source", "unknown")
                    triplet = f"{predecessor} {relation} {entity}"
                    graph_context.append(triplet)
            
            # Limit context size
            if len(graph_context) > 15:
                graph_context = graph_context[:15]
            
            # If no relevant triplets found
            if not graph_context:
                logger.info("No relevant information found in knowledge graph")
                return "No specific information about this topic was found in the knowledge graph."
            
            # Format context for generation
            context_text = "\n".join(graph_context)
            
            # Generate response based on knowledge graph
            if self.llm:
                # Try using LLM for better formatting
                kg_prompt = f"""
                Based only on these knowledge graph relationships, answer the question:
                
                {context_text}
                
                Question: {question}
                
                Provide a clear, concise answer using only the information above.
                """
                
                try:
                    kg_response = self.llm.predict(kg_prompt)
                    return kg_response
                except Exception as e:
                    logger.error(f"Error generating KG response with LLM: {str(e)}")
                    # Fall back to simple response
            
            # Simple response format if LLM fails or is not available
            kg_response = f"Based on the knowledge graph, I found these relationships:\n\n"
            
            # Group by patterns
            grouped_relations = {}
            for triplet in graph_context:
                parts = triplet.split(" ", 2)
                if len(parts) >= 3:
                    entity1, relation, entity2 = parts
                    if entity1 not in grouped_relations:
                        grouped_relations[entity1] = []
                    grouped_relations[entity1].append((relation, entity2))
            
            # Format response
            for entity, relations in grouped_relations.items():
                kg_response += f"• {entity}:\n"
                for relation, target in relations:
                    kg_response += f"  - {relation} {target}\n"
            
            return kg_response
            
        except Exception as e:
            logger.error(f"Error querying knowledge graph: {str(e)}", exc_info=True)
            return f"Error querying knowledge graph: {str(e)}"
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics about the knowledge graph.
        
        Returns:
            Dictionary with node and edge counts
        """
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges()
        }
    
    def get_node_connections(self, node: str) -> Dict[str, List[Dict[str, str]]]:
        """
        Get all connections for a specific node.
        
        Args:
            node: Node to get connections for
            
        Returns:
            Dictionary with outgoing and incoming connections
        """
        if not self.graph.has_node(node):
            return {"outgoing": [], "incoming": []}
        
        outgoing = []
        for successor in self.graph.successors(node):
            edge_data = self.graph.get_edge_data(node, successor)
            relation = edge_data.get("relation", "is related to")
            source = edge_data.get("source", "unknown")
            outgoing.append({
                "target": successor,
                "relation": relation,
                "source": source
            })
        
        incoming = []
        for predecessor in self.graph.predecessors(node):
            edge_data = self.graph.get_edge_data(predecessor, node)
            relation = edge_data.get("relation", "is related to")
            source = edge_data.get("source", "unknown")
            incoming.append({
                "source": predecessor,
                "relation": relation,
                "file": source
            })
        
        return {
            "outgoing": outgoing,
            "incoming": incoming
        }
    
    def get_top_entities(self, limit: int = 50) -> List[Tuple[str, int]]:
        """
        Get top entities by connection count.
        
        Args:
            limit: Maximum number of entities to return
            
        Returns:
            List of tuples (entity, connection_count)
        """
        if self.graph.number_of_nodes() == 0:
            return []
        
        entity_counts = sorted(
            [(node, self.graph.degree(node)) 
             for node in self.graph.nodes()],
            key=lambda x: x[1],
            reverse=True
        )
        
        return entity_counts[:limit]
    
    def get_relation_counts(self) -> List[Tuple[str, int]]:
        """
        Get counts of relationship types.
        
        Returns:
            List of tuples (relation_type, count)
        """
        if self.graph.number_of_edges() == 0:
            return []
        
        relation_counts = {}
        for u, v, data in self.graph.edges(data=True):
            relation = data.get("relation", "unknown")
            relation_counts[relation] = relation_counts.get(relation, 0) + 1
        
        # Sort by frequency
        sorted_relations = sorted(
            relation_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_relations
    
    def search_entities(self, search_term: str) -> List[str]:
        """
        Search for entities in the knowledge graph.
        
        Args:
            search_term: Term to search for
            
        Returns:
            List of matching entity names
        """
        if not search_term or self.graph.number_of_nodes() == 0:
            return []
        
        results = []
        for node in self.graph.nodes():
            if search_term.lower() in node.lower():
                results.append(node)
        
        return results
