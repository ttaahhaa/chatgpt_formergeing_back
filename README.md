# Document QA Assistant - Arabic Edition

A document question-answering system that works completely offline using AraberT for embeddings and Ollama for LLM inference.

## Directory Structure

This system expects the following directory structure:

```
document-qa-assistant/
├── app/                 # Application code
├── data/                # Data directory
│   ├── cache/           # Cache for processed documents
│   ├── conversations/   # Saved conversations
│   └── embeddings/      # Embedding models
│       └── arabert/     # AraberT model files
├── logs/                # Log files
├── setup.bat            # Setup script for Windows
├── setup.sh             # Setup script for Linux/macOS
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Prerequisites

- Python 3.10+ with pip
- [Ollama](https://ollama.ai/) installed and running
- AraberT model files in the `data/embeddings/arabert` directory

## Quick Setup

### Windows

1. Run the setup script:
   ```
   setup.bat
   ```

2. Start the application:
   ```
   streamlit run app/ui/streamlit_app.py
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

## Manual Installation

If the setup script doesn't work for you, follow these steps:

1. Create the necessary directories:
   ```
   mkdir -p data/embeddings data/cache data/conversations logs
   ```

2. Install the Python dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Place your AraberT model files in the `data/embeddings/arabert` directory

4. Start Ollama:
   ```
   ollama serve
   ```

5. Make sure the Mistral model is installed:
   ```
   ollama pull mistral:latest
   ```

6. Start the application:
   ```
   streamlit run app/ui/streamlit_app.py
   ```

## Using the Application

### Processing Documents

1. Upload Arabic documents (PDF, TXT, DOCX, etc.) using the sidebar
2. Click "Process Document" to extract text and create embeddings with AraberT
3. The processed documents will be stored in the vector database

### Asking Questions

1. Type your questions in Arabic in the "Ask Questions" tab
2. The system will:
   - Embed your question using AraberT
   - Find relevant document chunks using vector similarity
   - Pass the context to Ollama LLM to generate an answer

### Document Summarization

You can also upload Arabic documents for summarization in the "Summarize Document" tab.

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

## Advanced Configuration

You can tune the system by modifying parameters in `app/config.py`:

- `CHUNK_SIZE`: Size of document chunks (default: 1000 characters)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 200 characters)
- `EMBEDDING_BATCH_SIZE`: Number of chunks to embed at once (default: 16)
- `TOP_K_RETRIEVAL`: Number of document chunks to retrieve (default: 5)
- `HYBRID_ALPHA`: Balance between semantic and keyword search (default: 0.5)
