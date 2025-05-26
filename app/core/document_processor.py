"""
Enhanced document processor that builds knowledge graph during chunking.
"""

from typing import List, Dict
import re
import logging
from app.database.repositories import repository_factory

logger = logging.getLogger(__name__)

async def process_document_with_graph(document_id: str, document: dict, chunks: List[Dict]):
    """
    Process document chunks and build knowledge graph relationships.
    """
    try:
        kg_repo = repository_factory.knowledge_graph_repository
        
        # Get or create graph
        graph = await kg_repo.get_graph()
        if not graph:
            graph_id = await kg_repo.initialize_graph()
        else:
            graph_id = graph.id
        
        # Add document node
        doc_node_id = await kg_repo.add_node(
            graph_id=graph_id,
            label=document['filename'],
            node_type="document",
            properties={"document_id": document_id, "type": document.get('extension', 'unknown')}
        )
        
        # Process each chunk
        for idx, chunk in enumerate(chunks):
            # Extract entities from chunk
            entities = extract_chunk_entities(chunk['content'])
            
            # Add chunk node
            chunk_node_id = await kg_repo.add_node(
                graph_id=graph_id,
                label=f"Chunk {idx} of {document['filename']}",
                node_type="chunk",
                properties={
                    "document_id": document_id,
                    "chunk_index": idx,
                    "start": chunk['start'],
                    "end": chunk['end']
                }
            )
            
            # Connect chunk to document
            await kg_repo.add_edge(
                graph_id=graph_id,
                source_id=doc_node_id,
                target_id=chunk_node_id,
                relation="contains_chunk"
            )
            
            # Add entity nodes and relationships
            for entity in entities:
                # Add entity node
                entity_node_id = await kg_repo.add_node(
                    graph_id=graph_id,
                    label=entity['text'],
                    node_type=entity['type'],
                    properties={"document_id": document_id}
                )
                
                # Connect entity to chunk
                await kg_repo.add_edge(
                    graph_id=graph_id,
                    source_id=chunk_node_id,
                    target_id=entity_node_id,
                    relation="contains_entity"
                )
        
        logger.info(f"Built knowledge graph for document {document_id}")
        
    except Exception as e:
        logger.error(f"Error building knowledge graph: {str(e)}")


def extract_chunk_entities(text: str) -> List[Dict[str, str]]:
    """
    Extract entities from a chunk of text.
    """
    entities = []
    
    # Extract different types of entities
    # This is a simplified version - you could use spaCy or other NER tools
    
    # Technical terms
    tech_terms = re.findall(r'\b(?:API|SDK|HTTP|REST|JSON|XML|SQL|NoSQL|Docker|Kubernetes)\b', text, re.IGNORECASE)
    for term in tech_terms:
        entities.append({'text': term, 'type': 'technology'})
    
    # File paths
    file_paths = re.findall(r'(?:/[\w.-]+)+', text)
    for path in file_paths:
        entities.append({'text': path, 'type': 'file_path'})
    
    # URLs
    urls = re.findall(r'https?://[^\s]+', text)
    for url in urls:
        entities.append({'text': url, 'type': 'url'})
    
    # Class/function names (for code)
    if 'class ' in text or 'def ' in text:
        classes = re.findall(r'class\s+(\w+)', text)
        functions = re.findall(r'def\s+(\w+)', text)
        
        for cls in classes:
            entities.append({'text': cls, 'type': 'class'})
        for func in functions:
            entities.append({'text': func, 'type': 'function'})
    
    return entities 