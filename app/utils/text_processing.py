"""
Text processing utilities for Document QA Assistant.
Provides functions for text manipulation, sanitization, and language detection.
"""

import re
import logging
from typing import List, Dict, Any, Set, Optional

logger = logging.getLogger(__name__)

def sanitize_query(query: str, max_length: int = 1000) -> str:
    """
    Remove potentially harmful characters from a query.
    
    Args:
        query: User input query
        max_length: Maximum allowed length
        
    Returns:
        Sanitized query
    """
    try:
        # Remove potentially harmful characters
        sanitized = query.replace("'", "").replace(";", "").replace("<", "&lt;").replace(">", "&gt;")
        
        # Limit query length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            logger.warning(f"Query was truncated to {max_length} characters")
        
        return sanitized
    except Exception as e:
        logger.error(f"Error sanitizing query: {str(e)}")
        # Return a safe default if processing fails
        return query[:max_length] if query else ""

def detect_language(text: str) -> str:
    """
    Detect the language of a text.
    Simple implementation focused on distinguishing Arabic vs non-Arabic.
    
    Args:
        text: Text to analyze
        
    Returns:
        Language code (e.g., 'ar' for Arabic, 'en' for others)
    """
    try:
        # Arabic Unicode ranges
        arabic_ranges = [
            (0x0600, 0x06FF),  # Arabic
            (0x0750, 0x077F),  # Arabic Supplement
            (0x08A0, 0x08FF),  # Arabic Extended-A
            (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
            (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
        ]
        
        # Count Arabic characters
        arabic_count = 0
        total_count = 0
        
        for char in text:
            if not char.isspace():  # Skip whitespace
                code_point = ord(char)
                is_arabic = any(start <= code_point <= end for start, end in arabic_ranges)
                
                if is_arabic:
                    arabic_count += 1
                
                total_count += 1
        
        # Consider it Arabic if at least 20% of characters are Arabic
        if total_count > 10 and arabic_count / total_count >= 0.2:
            return "ar"
        else:
            return "en"  # Default to English for non-Arabic
    except Exception as e:
        logger.error(f"Error detecting language: {str(e)}")
        return "en"  # Default to English on error

def is_code_file(text: str) -> bool:
    """
    Determine if text is likely to be code.
    
    Args:
        text: Text content to analyze
        
    Returns:
        True if the content appears to be code, False otherwise
    """
    code_indicators = [
        'def ', 'class ', 'function', 'import ', 'from ', '#', '//', '/*', 
        'public ', 'private ', 'protected ', 'static ', 'void ', 'int ', 'string ',
        'const ', 'var ', 'let ', 'function(', '=>', '{', '};', 'return ', 'if(',
        'for(', 'while(', '@', 'package ', 'namespace '
    ]
    
    return any(indicator in text.lower() for indicator in code_indicators)

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract key terms/keywords from text.
    
    Args:
        text: Text to extract keywords from
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of extracted keywords
    """
    # Simple keyword extraction based on capitalization and frequency
    words = re.findall(r'\b[A-Za-z]\w+\b', text)
    
    # Count word frequency
    word_counts = {}
    for word in words:
        if len(word) > 3:  # Only consider words with more than 3 characters
            word_lower = word.lower()
            word_counts[word_lower] = word_counts.get(word_lower, 0) + 1
    
    # Sort by frequency
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Return top keywords
    keywords = [word for word, count in sorted_words[:max_keywords]]
    
    return keywords

def format_sources(sources: Set[str]) -> str:
    """
    Format source information for display.
    
    Args:
        sources: Set of source references
        
    Returns:
        Formatted source string
    """
    if not sources:
        return ""
    
    return "\n\nSources: " + ", ".join(sorted(sources))
