# app/core/embeddings.py
# Remove the self-import that's causing the circular dependency

import os
import logging
import numpy as np
from typing import List, Union, Optional
import torch
from pathlib import Path

logger = logging.getLogger(__name__)

class Embeddings:
    """Class for generating embeddings using a local ArabERT model."""
    
    def __init__(self, model_dir: Optional[str] = None):
        """
        Initialize the embeddings with a local ArabERT model.
        
        Args:
            model_dir: Directory containing the ArabERT model files
        """
        # Default to the project's embeddings directory if not specified
        if model_dir is None:
            model_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "embeddings", "arabert"
            )
        
        self.model_dir = model_dir
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Initialized embeddings with ArabERT model from {model_dir} on {self.device}")
    
    def load_model(self):
        """Load the ArabERT model and tokenizer if not already loaded."""
        if self.model is not None and self.tokenizer is not None:
            return
        
        try:
            from transformers import AutoModel, AutoTokenizer
            
            logger.info("Loading ArabERT model and tokenizer...")
            model_path = Path(self.model_dir)
            
            if not model_path.exists():
                raise FileNotFoundError(f"Model directory not found: {self.model_dir}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
            self.model = AutoModel.from_pretrained(self.model_dir).to(self.device)
            
            logger.info("ArabERT model and tokenizer loaded successfully")
            
        except ImportError as e:
            logger.error(f"Error importing transformers library: {str(e)}")
            raise ImportError("Required package 'transformers' not found. Please install it to use ArabERT embeddings.")
        except Exception as e:
            logger.error(f"Error loading ArabERT model: {str(e)}")
            raise RuntimeError(f"Failed to load ArabERT model: {str(e)}")
    
    def get_embeddings(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Generate embeddings for the given texts.
        
        Args:
            texts: A single text or list of texts to generate embeddings for
            
        Returns:
            numpy.ndarray of embeddings
        """
        try:
            # Load the model if not already loaded
            self.load_model()
            
            # Ensure texts is a list
            if isinstance(texts, str):
                texts = [texts]
            
            embeddings = []
            
            # Process in batches to avoid memory issues
            batch_size = 8
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                
                # Tokenize
                inputs = self.tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt"
                ).to(self.device)
                
                # Generate embeddings
                with torch.no_grad():
                    outputs = self.model(**inputs)
                
                # Use the [CLS] token embedding as the sentence embedding
                batch_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
                embeddings.extend(batch_embeddings)
            
            return np.array(embeddings)
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            # Return a zero vector as fallback
            return np.zeros((len(texts) if isinstance(texts, list) else 1, 768))
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity (float between -1 and 1)
        """
        try:
            # Normalize vectors
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return np.dot(embedding1, embedding2) / (norm1 * norm2)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0
    
    def check_model_status(self) -> dict:
        """Check if the ArabERT model is available and loaded."""
        try:
            model_path = Path(self.model_dir)
            model_files = list(model_path.glob("*"))
            
            if not model_path.exists():
                return {
                    "status": "unavailable",
                    "message": f"Model directory not found: {self.model_dir}"
                }
            
            if len(model_files) == 0:
                return {
                    "status": "unavailable",
                    "message": f"Model directory is empty: {self.model_dir}"
                }
            
            # Check for key model files
            required_files = ["config.json", "tokenizer_config.json"]
            missing_files = [f for f in required_files if not (model_path / f).exists()]
            
            if missing_files:
                return {
                    "status": "incomplete",
                    "message": f"Missing required model files: {', '.join(missing_files)}"
                }
            
            # Try loading the model to verify it works
            try:
                self.load_model()
                return {
                    "status": "available",
                    "message": f"ArabERT model loaded successfully from {self.model_dir}"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error loading model: {str(e)}"
                }
            
        except Exception as e:
            logger.error(f"Error checking model status: {str(e)}")
            return {
                "status": "error",
                "message": f"Error checking model status: {str(e)}"
            }