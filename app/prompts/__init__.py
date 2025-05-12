"""
Prompts package for managing different types of prompts.
"""

from .code_prompts import CODE_PROMPTS
from .general_prompts import GENERAL_PROMPTS
from .document_prompts import DOCUMENT_PROMPTS
from .conversation_prompts import CONVERSATION_PROMPTS
from .instructional_prompts import INSTRUCTIONAL_PROMPTS
from .example_prompts import EXAMPLE_PROMPTS
from .prompt_selector import prompt_selector

__all__ = ['CODE_PROMPTS', 'GENERAL_PROMPTS', 'DOCUMENT_PROMPTS', 
           'CONVERSATION_PROMPTS', 'INSTRUCTIONAL_PROMPTS', 'EXAMPLE_PROMPTS',
           'prompt_selector'] 