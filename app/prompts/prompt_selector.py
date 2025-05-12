"""
Prompt selector module to automatically choose appropriate prompts based on query context.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple

from .code_prompts import CODE_PROMPTS
from .general_prompts import GENERAL_PROMPTS
from .document_prompts import DOCUMENT_PROMPTS
from .conversation_prompts import CONVERSATION_PROMPTS
from .instructional_prompts import INSTRUCTIONAL_PROMPTS
from .example_prompts import EXAMPLE_PROMPTS

logger = logging.getLogger(__name__)

class PromptSelector:
    """Selects appropriate prompts based on query content and conversation context."""
    
    def __init__(self):
        """Initialize the prompt selector with pattern dictionaries."""
        # Define patterns for different types of queries
        self.code_patterns = [
            r'code', r'function', r'(java|python|javascript|typescript|c\+\+|ruby|go|rust|php|html|css)',
            r'programming', r'algorithm', r'compile', r'runtime', r'syntax', r'error', r'bug', r'debug',
            r'class', r'method', r'variable', r'library', r'framework', r'api', r'sdk', r'dependency',
            r'(git|github|gitlab)', r'docker', r'kubernetes', r'deploy', r'server', r'database', r'sql',
            r'npm', r'pip', r'yarn', r'cargo', r'gradle', r'maven', r'webpack', r'babel', r'linter'
        ]
        
        self.document_patterns = [
            r'document', r'documentation', r'manual', r'guide', r'tutorial', r'pdf', r'book',
            r'reference', r'specification', r'api doc', r'user guide', r'technical doc', 
            r'chapter', r'section', r'page', r'diagram', r'figure', r'table', r'appendix',
            r'report', r'paper', r'publication', r'article'
        ]
        
        self.instructional_patterns = [
            r'how (to|do|can|would|should)', r'step[s]?', r'guide', r'tutorial', r'learn',
            r'teach', r'explain', r'instruction', r'procedure', r'process', r'method',
            r'beginner', r'start', r'introduction', r'basic', r'fundamental', r'compare',
            r'versus', r'vs\.', r'difference', r'similar', r'better', r'best practice',
            r'recommendation', r'suggest', r'advice', r'tip'
        ]
        
        self.conversation_patterns = [
            r'earlier', r'previous', r'before', r'you said', r'you mentioned', r'follow[- ]up',
            r'continuing', r'also', r'additionally', r'furthermore', r'moreover',
            r'related to', r'regarding', r'concerning', r'about that', r'on that note',
            r'another question', r'clarify', r'clarification', r'confused', r'understand',
            r'mean[t]?', r'specifically', r'precisely', r'exactly', r'correction', r'correct'
        ]

        self.comparison_patterns = [
            r'compare', r'comparison', r'versus', r'vs', r'difference', r'similarities',
            r'better', r'advantages', r'disadvantages', r'pros', r'cons', r'trade[\s-]?offs',
            r'which is', r'preferred', r'alternative', r'options'
        ]

        self.troubleshooting_patterns = [
            r'trouble', r'issue', r'problem', r'error', r'not working', r'broken', r'fix',
            r'debug', r'solve', r'solution', r'resolve', r'help', r'stuck', r'fails',
            r'won\'t', r'doesn\'t', r'isn\'t', r'aren\'t', r'can\'t', r'couldn\'t'
        ]

        self.step_by_step_patterns = [
            r'step[s]?', r'procedure', r'how to', r'guide', r'walkthrough', r'tutorial',
            r'instructions', r'process', r'setup', r'configure', r'install', r'build',
            r'create', r'implement', r'develop', r'make', r'do'
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = {
            'code': [re.compile(r, re.IGNORECASE) for r in self.code_patterns],
            'document': [re.compile(r, re.IGNORECASE) for r in self.document_patterns],
            'instructional': [re.compile(r, re.IGNORECASE) for r in self.instructional_patterns],
            'conversation': [re.compile(r, re.IGNORECASE) for r in self.conversation_patterns],
            'comparison': [re.compile(r, re.IGNORECASE) for r in self.comparison_patterns],
            'troubleshooting': [re.compile(r, re.IGNORECASE) for r in self.troubleshooting_patterns],
            'step_by_step': [re.compile(r, re.IGNORECASE) for r in self.step_by_step_patterns]
        }
        
        logger.info("PromptSelector initialized with query pattern matchers")
    
    def _match_patterns(self, text: str, patterns: List[re.Pattern]) -> bool:
        """Check if text matches any of the provided compiled patterns."""
        return any(pattern.search(text) for pattern in patterns)
    
    def _detect_query_type(self, query: str, conversation_context: Optional[List[Dict[str, str]]] = None) -> Dict[str, float]:
        """
        Detect the query type based on patterns and context.
        
        Args:
            query: The user's query
            conversation_context: Previous messages in the conversation
            
        Returns:
            Dictionary of query type scores (0.0-1.0)
        """
        scores = {
            'code': 0.0,
            'document': 0.0,
            'instructional': 0.0,
            'conversation': 0.0,
            'comparison': 0.0,
            'troubleshooting': 0.0,
            'step_by_step': 0.0,
            'general': 0.0  # Default
        }
        
        # Check if the query matches any of our patterns
        if self._match_patterns(query, self.compiled_patterns['code']):
            scores['code'] = 0.8
        
        if self._match_patterns(query, self.compiled_patterns['document']):
            scores['document'] = 0.8
        
        if self._match_patterns(query, self.compiled_patterns['instructional']):
            scores['instructional'] = 0.8
        
        if self._match_patterns(query, self.compiled_patterns['comparison']):
            scores['comparison'] = 0.8
        
        if self._match_patterns(query, self.compiled_patterns['troubleshooting']):
            scores['troubleshooting'] = 0.8
        
        if self._match_patterns(query, self.compiled_patterns['step_by_step']):
            scores['step_by_step'] = 0.8
        
        # Check for conversation context indicators
        has_context = conversation_context is not None and len(conversation_context) > 1
        if has_context or self._match_patterns(query, self.compiled_patterns['conversation']):
            scores['conversation'] = 0.9 if has_context else 0.7
        
        # Ensure general knowledge always has some weight
        scores['general'] = 0.5
        
        # Normalize scores if needed
        total = sum(scores.values())
        if total > 0:
            for key in scores:
                scores[key] = scores[key] / total
        
        logger.debug(f"Query type scores: {scores}")
        return scores
    
    def select_system_prompt(self, query: str, conversation_context: Optional[List[Dict[str, str]]] = None, 
                           document_mode: bool = False) -> str:
        """
        Select the most appropriate system prompt based on the query and context.
        
        Args:
            query: The user's query
            conversation_context: Previous messages in the conversation
            document_mode: Whether document mode is enabled
            
        Returns:
            Selected system prompt
        """
        # Override with document prompt if in document mode
        if document_mode:
            return DOCUMENT_PROMPTS["system"]
        
        # Get query type scores
        scores = self._detect_query_type(query, conversation_context)
        
        # Select the prompt based on the highest score
        max_type = max(scores.items(), key=lambda x: x[1])[0]
        
        if max_type == 'code':
            prompt = CODE_PROMPTS["system"]
        elif max_type == 'document':
            prompt = DOCUMENT_PROMPTS["system"]
        elif max_type == 'instructional':
            prompt = INSTRUCTIONAL_PROMPTS["system"]
        elif max_type == 'conversation':
            prompt = CONVERSATION_PROMPTS["system"]
        else:
            prompt = GENERAL_PROMPTS["system"]
        
        logger.info(f"Selected {max_type} system prompt based on query analysis")
        return prompt
    
    def select_example_prompt(self, query: str) -> Optional[str]:
        """
        Select an appropriate example prompt based on the query type.
        
        Args:
            query: The user's query
            
        Returns:
            Selected example prompt or None
        """
        scores = self._detect_query_type(query)
        
        # Determine the type of example to provide
        if scores['troubleshooting'] > 0.3:
            return EXAMPLE_PROMPTS["troubleshooting_example"]
        elif scores['comparison'] > 0.3:
            return EXAMPLE_PROMPTS["comparison_example"]
        elif scores['step_by_step'] > 0.3:
            return EXAMPLE_PROMPTS["step_by_step_example"]
        elif scores['code'] > 0.3:
            # Check if it's a programming question specifically
            programming_keywords = ['code', 'function', 'program', 'script', 'python', 'javascript', 'java', 'c++']
            if any(keyword in query.lower() for keyword in programming_keywords):
                return EXAMPLE_PROMPTS["programming_example"]
            return EXAMPLE_PROMPTS["technical_example"]
        elif scores['general'] > 0.3:
            return EXAMPLE_PROMPTS["general_example"]
        
        return None
    
    def enhance_with_context_prompts(self, query: str, system_prompt: str, 
                                    conversation_context: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Enhance the system prompt with additional context-specific prompts.
        
        Args:
            query: The user's query
            system_prompt: Base system prompt
            conversation_context: Previous messages in the conversation
            
        Returns:
            Enhanced system prompt
        """
        additional_prompts = []
        scores = self._detect_query_type(query, conversation_context)
        
        # Add secondary prompts for strong matches (threshold 0.3 after normalization)
        # Handle code-specific aspects
        if scores['code'] > 0.3:
            if 'error' in query.lower() or 'bug' in query.lower() or 'fix' in query.lower() or 'issue' in query.lower():
                additional_prompts.append(CODE_PROMPTS["error_handling"])
            elif 'optimiz' in query.lower() or 'performance' in query.lower() or 'faster' in query.lower() or 'efficien' in query.lower():
                additional_prompts.append(CODE_PROMPTS["optimization"])
            elif 'review' in query.lower() or 'improve' in query.lower() or 'better' in query.lower() or 'best practice' in query.lower():
                additional_prompts.append(CODE_PROMPTS["code_review"])
            elif 'debug' in query.lower() or 'troubleshoot' in query.lower() or 'diagnose' in query.lower():
                additional_prompts.append(CODE_PROMPTS["debugging"])
        
        # Handle document-specific aspects
        if scores['document'] > 0.3:
            if 'api' in query.lower() or 'endpoint' in query.lower() or 'interface' in query.lower():
                additional_prompts.append(DOCUMENT_PROMPTS["api_documentation"])
            elif 'code' in query.lower() or 'function' in query.lower() or 'class' in query.lower() or 'method' in query.lower():
                additional_prompts.append(DOCUMENT_PROMPTS["code_documentation"])
            elif 'system' in query.lower() or 'architecture' in query.lower() or 'design' in query.lower() or 'component' in query.lower():
                additional_prompts.append(DOCUMENT_PROMPTS["system_documentation"])
            elif 'technical' in query.lower() or 'specification' in query.lower() or 'requirement' in query.lower():
                additional_prompts.append(DOCUMENT_PROMPTS["technical_document"])
            elif 'learn' in query.lower() or 'course' in query.lower() or 'tutorial' in query.lower() or 'lesson' in query.lower():
                additional_prompts.append(DOCUMENT_PROMPTS["educational_document"])
                
        # Handle instructional aspects
        if scores['instructional'] > 0.3:
            if 'technical' in query.lower() or 'advanced' in query.lower() or 'expert' in query.lower():
                additional_prompts.append(INSTRUCTIONAL_PROMPTS["technical_how_to"])
            elif 'beginner' in query.lower() or 'start' in query.lower() or 'new to' in query.lower() or 'basic' in query.lower():
                additional_prompts.append(INSTRUCTIONAL_PROMPTS["beginner_guide"])
            elif 'compare' in query.lower() or 'versus' in query.lower() or 'vs' in query.lower() or 'difference' in query.lower():
                additional_prompts.append(INSTRUCTIONAL_PROMPTS["comparative_teaching"])
            elif 'troubleshoot' in query.lower() or 'fix' in query.lower() or 'solve' in query.lower() or 'problem' in query.lower():
                additional_prompts.append(INSTRUCTIONAL_PROMPTS["troubleshooting"])
            elif 'learn' in query.lower() or 'roadmap' in query.lower() or 'path' in query.lower() or 'curriculum' in query.lower():
                additional_prompts.append(INSTRUCTIONAL_PROMPTS["learning_progression"])
                
        # Handle conversation aspects
        if scores['conversation'] > 0.3 and conversation_context and len(conversation_context) > 1:
            if 'clarify' in query.lower() or 'what do you mean' in query.lower() or 'understand' in query.lower():
                additional_prompts.append(CONVERSATION_PROMPTS["clarification"])
            elif 'follow' in query.lower() or 'continue' in query.lower() or 'more on' in query.lower() or 'elaborate' in query.lower():
                additional_prompts.append(CONVERSATION_PROMPTS["follow_up"])
            elif query.count('?') > 1 or ';' in query or 'and also' in query.lower() or 'also' in query.lower():
                additional_prompts.append(CONVERSATION_PROMPTS["multi_question"])
            elif 'correct' in query.lower() or 'wrong' in query.lower() or 'mistake' in query.lower() or 'error' in query.lower():
                additional_prompts.append(CONVERSATION_PROMPTS["correction"])
                
        # Add general response structure prompts
        additional_prompts.append(GENERAL_PROMPTS["response_structure"])
        
        # Add an appropriate example prompt if available
        example_prompt = self.select_example_prompt(query)
        if example_prompt:
            additional_prompts.append(example_prompt)
        
        # Combine prompts
        if additional_prompts:
            combined_prompt = system_prompt + "\n\nAdditional guidance:\n\n" + "\n\n".join(additional_prompts)
        else:
            combined_prompt = system_prompt
            
        return combined_prompt
    
    def get_enhanced_prompt(self, query: str, 
                           conversation_context: Optional[List[Dict[str, str]]] = None,
                           document_mode: bool = False) -> str:
        """
        Get a fully enhanced prompt for the given query and context.
        
        Args:
            query: The user's query
            conversation_context: Previous messages in the conversation
            document_mode: Whether document mode is enabled
            
        Returns:
            Enhanced prompt for the LLM
        """
        # First select the base system prompt
        system_prompt = self.select_system_prompt(query, conversation_context, document_mode)
        
        # Then enhance it with additional context prompts
        enhanced_prompt = self.enhance_with_context_prompts(query, system_prompt, conversation_context)
        
        return enhanced_prompt

# Create a singleton instance
prompt_selector = PromptSelector() 