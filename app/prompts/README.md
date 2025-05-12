# Enhanced Prompting System for Small LLMs

This directory contains the enhanced prompting system designed to improve the performance of smaller, less powerful LLMs. The system dynamically selects and combines prompts based on query context to provide better guidance to the LLM.

## How It Works

1. **Query Analysis**: When a user submits a query, the `PromptSelector` analyzes the query for patterns that indicate the type of question.
2. **Prompt Selection**: Based on the analysis, it selects the most appropriate system prompt.
3. **Prompt Enhancement**: It then adds specialized sub-prompts based on specific keywords and patterns in the query.
4. **Example Selection**: It includes relevant examples that match the query type to demonstrate proper response patterns.
5. **Combined Prompt**: The combined prompt is sent to the LLM, providing clear, structured guidance for generating a response.

## Prompt Categories

### General Prompts (`general_prompts.py`)
- **System**: Core directions for accurate, informative responses
- **Technical**: Guidelines for technical explanations
- **Conceptual**: Framework for explaining abstract concepts
- **Factual**: Pattern for providing factual information
- **Response Structure**: Guidelines for organizing responses effectively

### Code Prompts (`code_prompts.py`)
- **System**: Framework for answering programming questions
- **Error Handling**: Guidelines for debugging and error resolution
- **Optimization**: Structure for code performance improvements
- **Code Review**: Framework for evaluating code quality
- **Debugging**: Process for troubleshooting code issues

### Document Prompts (`document_prompts.py`)
- **System**: Framework for document-based responses
- **Code Documentation**: Guidelines for explaining code docs
- **API Documentation**: Structure for explaining API docs
- **System Documentation**: Framework for system architecture docs
- **Technical Document**: Guidelines for technical specifications
- **Educational Document**: Structure for learning materials

### Conversation Prompts (`conversation_prompts.py`)
- **System**: Framework for multi-turn conversations
- **Clarification**: Guidelines for resolving ambiguities
- **Follow-up**: Structure for building on previous answers
- **Multi-Question**: Framework for handling multiple questions
- **Correction**: Guidelines for correcting previous information

### Instructional Prompts (`instructional_prompts.py`)
- **System**: Framework for step-by-step instructions
- **Technical How-To**: Guidelines for technical processes
- **Beginner Guide**: Structure for teaching new concepts
- **Comparative Teaching**: Framework for comparing approaches
- **Troubleshooting**: Guidelines for problem diagnosis
- **Learning Progression**: Structure for creating learning paths

### Example Prompts (`example_prompts.py`)
- **General Example**: Sample answers to general knowledge questions
- **Technical Example**: Sample answers to technical explanations
- **Step-by-Step Example**: Sample procedural instructions
- **Comparison Example**: Sample comparative analyses
- **Troubleshooting Example**: Sample problem-solving responses

## Prompt Selection Logic

The `PromptSelector` in `prompt_selector.py` uses pattern matching to classify queries:

1. **Code Detection**: Identifies programming-related terms, languages, frameworks
2. **Document Detection**: Recognizes references to documentation, manuals, guides
3. **Instruction Detection**: Spots how-to questions, tutorials, comparisons
4. **Conversation Detection**: Identifies references to previous messages, clarifications
5. **Comparison Detection**: Recognizes requests to compare or contrast items
6. **Troubleshooting Detection**: Identifies problem-solving or issue-resolution requests
7. **Step-by-Step Detection**: Recognizes requests for procedural instructions

## Why Examples Improve Small LLM Performance

Including examples in prompts significantly improves small LLM performance by:

1. **Demonstrating Response Patterns**: Examples show the expected structure, depth, and tone
2. **Reducing Hallucinations**: By modeling factual, accurate responses in examples
3. **Improving Output Format**: Helping the model understand how to organize information
4. **In-Context Learning**: Leveraging the model's ability to learn patterns from examples
5. **Providing Context Boundaries**: Showing appropriate level of detail and scope for answers

## Customizing Prompts

To customize the prompts:

1. Edit the appropriate prompt file to modify existing prompts
2. Add new prompt categories by creating new entries in the dictionaries
3. Update the `PromptSelector` to recognize and use new prompt categories
4. Add new examples that demonstrate ideal response patterns

When customizing, remember:
- Keep instructions clear and concise
- Use numbered lists for step-by-step guidance
- Focus on explicit, concrete instructions
- Consider the limitations of small LLMs
- Provide diverse, high-quality examples

## Integration with the LLM

The prompting system is integrated in the `LLMChain` class, which:
1. Gets enhanced prompts from the selector
2. Adds them as system messages
3. Manages conversation history
4. Handles document-based queries with specialized prompts
5. Includes relevant examples based on query type

This design significantly improves the quality of responses from smaller LLMs by providing clear, structured guidance tailored to each query and reinforcing appropriate response patterns through relevant examples. 