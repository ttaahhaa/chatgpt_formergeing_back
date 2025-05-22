# Document QA Assistant - Arabic Edition

A comprehensive document question-answering system that works completely offline using AraberT for embeddings and Ollama for LLM inference. The system provides a hybrid RAG (Retrieval-Augmented Generation) approach combining vector-based similarity search with knowledge graph-based retrieval.

## System Overview

The Document QA Assistant is designed to:

1. Process and index Arabic documents using AraberT embeddings
2. Store documents and their vector representations in MongoDB
3. Retrieve relevant document chunks using hybrid semantic and keyword search
4. Generate accurate answers using local LLMs through Ollama integration
5. Provide conversation memory and document context awareness
6. Support document summarization and knowledge graph creation
7. Work entirely offline without external API dependencies

## Features

- **Complete Offline Operation**: All processing happens locally without external API calls
- **MongoDB Integration**: Robust document storage with proper indexing and retrieval
- **Hybrid Retrieval**: Combines semantic vector search with keyword-based matching
- **Enhanced Prompting System**: Dynamic prompt selection based on query context
- **Multi-Document Processing**: Support for PDF, TXT, DOCX, and other file formats
- **Knowledge Graph**: Extracts relationships between document entities
- **Streaming Responses**: Real-time token-by-token generation for a smoother UX
- **User Authentication**: Full user management with JWT authentication
- **Conversation History**: Tracks and maintains context across multi-turn interactions
- **Document Sharing**: Ability to share documents between users
- **Arabic-First Design**: Optimized for Arabic text with AraberT embeddings

## Architecture

The system follows a modular architecture with these key components:

### Core Components
- **Document Loader**: Processes various file types (PDF, DOCX, TXT, code files)
- **Embeddings**: Uses AraberT models for Arabic text embeddings
- **Vector Store**: Hybrid MongoDB/FAISS storage for efficient similarity search
- **LLM Chain**: Interfaces with local Ollama models for text generation
- **Knowledge Graph**: Builds relationship graphs from document entities
- **Hybrid Retriever**: Combines vector similarity with keyword-based retrieval

### MongoDB Integration
- **Document Repository**: Stores document metadata and content
- **Embedding Repository**: Manages vector embeddings for similarity search
- **Conversation Repository**: Persists conversation history
- **User Repository**: Handles user authentication and management
- **Knowledge Graph Repository**: Stores document knowledge graphs

### API Layer
- **FastAPI Backend**: RESTful API with proper authentication and error handling
- **Streaming Support**: Real-time response generation with server-sent events
- **File Upload/Processing**: Secure document upload and processing

## Prerequisites

- Python 3.10+ with pip
- [Ollama](https://ollama.ai/) installed and running
- MongoDB server running (or use the included configuration for localhost)
- AraberT model files in the `data/embeddings/arabert` directory

## Installation

### Windows

1. Run the setup script:
   ```
   setup.bat
   ```

2. Start the application:
   ```
   streamlit run app/ui/streamlit_app.py
   ```
   
   OR for API-only mode:
   ```
   python -m uvicorn app.main:app --reload
   ```

### Linux/macOS

1. Run the setup script:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. Start the application:
   ```bash
   streamlit run app/ui/streamlit_app.py
   ```
   
   OR for API-only mode:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

## AraberT Model Installation

The system expects your AraberT model files to be located in the `data/embeddings/arabert` directory. This directory should contain the standard Hugging Face Transformers model files, such as:

- `config.json`
- `pytorch_model.bin` (or model files split into pieces)
- `tokenizer_config.json`
- `vocab.txt` or equivalent tokenizer files

If you have the AraberT model files in a different location, you can either:

1. Create a symbolic link:
   ```
   mklink /D data\embeddings\arabert C:\path\to\your\arabert\model   # Windows
   ln -s /path/to/your/arabert/model data/embeddings/arabert         # Linux/macOS
   ```

2. Copy the model files to the expected location:
   ```
   xcopy /E /I C:\path\to\your\arabert\model data\embeddings\arabert  # Windows
   cp -r /path/to/your/arabert/model data/embeddings/arabert          # Linux/macOS
   ```

3. Edit the path in `app/config.py`:
   ```python
   EMBEDDING_MODEL_PATH: Path = BASE_DIR / "path" / "to" / "your" / "arabert" / "model"
   ```

## Ollama Setup

The system requires Ollama for LLM inference. Make sure Ollama is running and the required models are installed:

1. Start Ollama:
   ```
   ollama serve
   ```

2. Install the Mistral model:
   ```
   ollama pull mistral:latest
   ```

3. Verify Ollama is working:
   ```
   ollama list
   ```

## MongoDB Configuration

The system uses MongoDB for document and embedding storage. Default configuration connects to a local MongoDB instance. You can modify the connection settings in `app/database/config.py`:

```python
# MongoDB connection settings
self.host = os.getenv("MONGODB_HOST", "localhost")
self.port = int(os.getenv("MONGODB_PORT", "27017"))
self.username = os.getenv("MONGODB_USERNAME", "admin")
self.password = os.getenv("MONGODB_PASSWORD", "P@ssw0rd")
self.database_name = os.getenv("MONGODB_DATABASE", "document_qa")
```

## Using the Application

### Processing Documents

1. Upload Arabic documents (PDF, TXT, DOCX, etc.) using the upload interface
2. Click "Process Document" to extract text and create embeddings with AraberT
3. The processed documents will be stored in the vector database

### Asking Questions

1. Type your questions in Arabic (or English) in the chat interface
2. The system will:
   - Embed your question using AraberT
   - Find relevant document chunks using hybrid vector similarity
   - Pass the context to Ollama LLM to generate an answer
   - Include source citations in the response

### Document Summarization

You can also upload Arabic documents for summarization in the "Summarize Document" tab.

### Knowledge Graph

The system can build knowledge graphs from your documents, extracting relationships between entities to enhance question answering.

### User Management

The system supports multiple users with different permission levels:

- **admin**: Full system access
- **chat_user**: Basic chat capabilities
- **chat_user_with_documents**: Chat and document upload/management
- **settings_user_with_documents**: Chat, documents, and system settings

## Advanced Configuration

You can tune the system by modifying parameters in `app/config.py`:

- `CHUNK_SIZE`: Size of document chunks (default: 1000 characters)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 200 characters)
- `EMBEDDING_BATCH_SIZE`: Number of chunks to embed at once (default: 16)
- `TOP_K_RETRIEVAL`: Number of document chunks to retrieve (default: 5)
- `HYBRID_ALPHA`: Balance between semantic and keyword search (default: 0.5)
- `LLM_MAX_TOKENS`: Maximum tokens for LLM responses (default: 1024)
- `LLM_TEMPERATURE`: Temperature setting for LLM responses (default: 0.1)

## Enhanced Prompting System

The system includes an advanced prompting system designed specifically to improve the performance of smaller, less powerful LLMs:

### Key Features

1. **Context-Aware Prompt Selection**: Automatically selects the most appropriate prompt based on query analysis
2. **Comprehensive Prompt Categories**:
   - General knowledge prompts
   - Code-specific prompts
   - Document-based prompts
   - Conversation prompts for multi-turn interactions
   - Instructional prompts for how-to questions

3. **Dynamic Prompt Enhancement**: Combines multiple prompts based on the query context for more targeted responses

4. **Optimized for Small LLMs**:
   - Clear, structured guidance with numbered points
   - Concrete instructions for different query types
   - Explicit formatting and organization guidance

## API Endpoints

The system exposes a RESTful API for integration with other applications:

### Document Endpoints
- `POST /api/upload`: Upload a document
- `GET /api/documents`: Get all documents
- `POST /api/delete_document`: Delete a document
- `POST /api/clear_documents`: Clear all documents
- `POST /api/rebuild_index`: Rebuild the FAISS index

### Chat Endpoints
- `POST /api/chat`: Send a chat message and get a response
- `POST /api/chat/stream`: Stream a chat response token by token

### Conversation Endpoints
- `POST /api/conversations/new`: Create a new conversation
- `GET /api/conversations`: Get all conversations
- `GET /api/conversations/{conversation_id}`: Get a specific conversation
- `POST /api/conversations/save`: Save a conversation
- `POST /api/conversations/clear`: Clear all conversations
- `DELETE /api/conversations/{conversation_id}`: Delete a conversation

### User Endpoints
- `POST /api/users/login`: Authenticate a user
- `GET /api/users/me`: Get current user info
- `POST /api/users/change-password`: Change user password

### System Endpoints
- `GET /api/status`: Get system status
- `GET /api/check_ollama`: Check Ollama status
- `GET /api/models`: Get available models
- `POST /api/set_model`: Set LLM model
- `POST /api/clear_cache`: Clear system cache

## Troubleshooting

### AraberT Model Not Found

If the application can't find your AraberT model:

1. Check the expected path: `./data/embeddings/arabert`
2. Make sure this directory exists and contains the model files
3. Check the application logs for specific errors

### Out of Memory Errors

If you encounter memory issues when processing documents:

1. Reduce `EMBEDDING_BATCH_SIZE` in `app/config.py` (default: 16)
2. Process smaller documents or reduce the chunk size
3. Use a GPU if available (the system automatically detects and uses CUDA if available)

### Ollama Connection Issues

If you encounter issues connecting to Ollama:

1. Ensure Ollama is running: `ollama serve`
2. Verify the models are downloaded: `ollama list`
3. Check the Ollama API URL in `app/config.py` (default: `http://localhost:11434`)

### MongoDB Connection Issues

If the system can't connect to MongoDB:

1. Verify MongoDB is running: `mongod --version`
2. Check MongoDB connection settings in `app/database/config.py`
3. Try creating the database manually: `mongo` then `use document_qa`

## License and Attribution

This project is built using various open-source components:

- AraberT: For Arabic language embeddings
- Ollama: For local LLM inference
- MongoDB: For document and embedding storage
- FastAPI: For the REST API backend
- PyTorch: For running the embedding models
- FAISS: For efficient vector similarity search

Please respect the licenses of all included components when using this software.

## Contributing

Contributions to improve the Document QA Assistant are welcome. Please feel free to submit issues or pull requests to enhance the functionality.
