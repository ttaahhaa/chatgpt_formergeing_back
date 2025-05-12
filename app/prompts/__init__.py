"""
Prompts package for managing different types of prompts.
"""

from .code_prompts import CODE_PROMPTS
from .general_prompts import GENERAL_PROMPTS
from .document_prompts import DOCUMENT_PROMPTS

__all__ = ['CODE_PROMPTS', 'GENERAL_PROMPTS', 'DOCUMENT_PROMPTS'] 