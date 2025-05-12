# Update app/core/llm.py to use local Ollama models instead of remote APIs

import os
import logging
import requests
import json
from typing import List, Dict, Any, Optional

from app.prompts import prompt_selector

logger = logging.getLogger(__name__)

class LLMChain:
    """Class for generating responses using a local LLM through Ollama."""
    
    def __init__(self, model_name: str = "mistral:latest"):
        """
        Initialize the LLM chain with a local Ollama model.
        
        Args:
            model_name: Name of the Ollama model to use (default: llama2)
        """
        self.model_name = model_name
        self.ollama_base_url = "http://localhost:11434"  # Default Ollama API endpoint
        logger.info(f"Initialized LLM chain with local Ollama model: {self.model_name}")
    
    def generate_response(self, query: str, conversation_context: List[Dict[str, str]]) -> str:
        """
        Generate a response to the given query using local Ollama model.
        
        Args:
            query: The user's query
            conversation_context: List of previous messages in the conversation
            
        Returns:
            The generated response
        """
        try:
            if not query:
                return "I didn't receive a question. How can I help you?"
            
            # Get enhanced prompt using prompt selector
            enhanced_system_prompt = prompt_selector.get_enhanced_prompt(
                query=query,
                conversation_context=conversation_context
            )
            
            # Format conversation context for Ollama
            messages = []
            
            # Add system prompt as the first message
            messages.append({
                "role": "system",
                "content": enhanced_system_prompt
            })
            
            # Add context messages (skipping any existing system messages)
            if conversation_context:
                for msg in conversation_context:
                    if msg["role"] != "system":  # Skip old system messages
                        messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
            
            # Add current query
            messages.append({
                "role": "user",
                "content": query
            })
            
            # Use chat completion for all queries to benefit from the enhanced system prompt
            return self._generate_with_ollama_chat(messages)
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"I encountered an error while processing your question: {str(e)}"
    
    def _generate_with_ollama_completion(self, prompt: str) -> str:
        """Generate response using Ollama completion API."""
        try:
            url = f"{self.ollama_base_url}/api/generate"
            
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return f"Error: Unable to get response from Ollama (Status: {response.status_code})"
                
        except requests.exceptions.ConnectionError:
            logger.error("Connection error: Unable to connect to Ollama API")
            return "Error: Unable to connect to the local Ollama service. Please ensure Ollama is running."
        except Exception as e:
            logger.error(f"Error in Ollama completion: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    def _generate_with_ollama_chat(self, messages: List[Dict[str, str]]) -> str:
        """Generate response using Ollama chat API."""
        try:
            url = f"{self.ollama_base_url}/api/chat"
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "")
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return f"Error: Unable to get response from Ollama (Status: {response.status_code})"
                
        except requests.exceptions.ConnectionError:
            logger.error("Connection error: Unable to connect to Ollama API")
            return "Error: Unable to connect to the local Ollama service. Please ensure Ollama is running."
        except Exception as e:
            logger.error(f"Error in Ollama chat: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    def query_with_sources(self, query: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a response with source citations.
        
        Args:
            query: The user's query
            documents: List of relevant documents
            
        Returns:
            Dict containing the response and sources
        """
        try:
            # Get enhanced prompt for document-based questions
            enhanced_system_prompt = prompt_selector.get_enhanced_prompt(
                query=query,
                document_mode=True
            )
            
            # Prepare document context
            context_prompt = ""
            sources = []
            
            # Format document content as context
            if documents:
                context_prompt = "Here are some relevant documents to help answer the query:\n\n"
                
                for i, doc in enumerate(documents[:3]):  # Limit to 3 sources for context
                    doc_name = doc.get("filename", f"Document {i+1}")
                    doc_content = doc.get("content", "")
                    
                    # Truncate very long content
                    if len(doc_content) > 1500:
                        doc_content = doc_content[:1500] + "..."
                    
                    context_prompt += f"--- Document: {doc_name} ---\n{doc_content}\n\n"
                    
                    # Add to sources list
                    sources.append({
                        "document": doc_name,
                        "relevance": 0.9 - (i * 0.2)  # Mock relevance scores
                    })
            
            # Create messages for chat API
            messages = [
                {
                    "role": "system",
                    "content": enhanced_system_prompt
                },
                {
                    "role": "user",
                    "content": f"{context_prompt}Based on the above documents, please answer this question: {query}"
                }
            ]
            
            # Get the response using chat completion
            response = self._generate_with_ollama_chat(messages)
            
            return {
                "response": response,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"Error generating response with sources: {str(e)}")
            return {
                "response": f"I encountered an error while processing your question: {str(e)}",
                "sources": []
            }

    def check_ollama_status(self) -> Dict[str, Any]:
        """Check if Ollama is available and which models are installed."""
        try:
            # Check if Ollama is running by listing models
            url = f"{self.ollama_base_url}/api/tags"
            response = requests.get(url)
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                return {
                    "status": "available",
                    "models": [model.get("name") for model in models]
                }
            else:
                return {
                    "status": "error",
                    "message": f"Ollama API error: {response.status_code} - {response.text}"
                }
                
        except requests.exceptions.ConnectionError:
            logger.error("Connection error: Unable to connect to Ollama API")
            return {
                "status": "unavailable",
                "message": "Unable to connect to the local Ollama service. Please ensure Ollama is running."
            }
        except Exception as e:
            logger.error(f"Error checking Ollama status: {str(e)}")
            return {
                "status": "error",
                "message": f"Error checking Ollama status: {str(e)}"
            }