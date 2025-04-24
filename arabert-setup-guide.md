# Setting Up Document QA with AraberT - Setup Guide

This guide explains how to set up the Document QA system to work with your local AraberT model for Arabic language processing.

## Prerequisites

1. Your local AraberT model files in `\data\embeddings\arabert`
2. Ollama installed and running with a suitable LLM model
3. Python 3.10+ installed on your system

## Installation Steps

### 1. Install Python Dependencies

First, install all required Python packages:

```bash
pip install -r requirements.txt
```

The requirements include:
- `transformers` and `torch` for working with AraberT
- `faiss-cpu` for vector similarity search
- `streamlit` for the web interface
- Other document processing libraries

### 2. Verify AraberT Model Structure

Ensure your AraberT model directory has the expected structure. A typical Hugging Face transformer model directory should contain:

- `config.json`
- `pytorch_model.bin` (or model files split into pieces)
- `tokenizer_config.json`
- `vocab.txt` or equivalent tokenizer files

### 3. Configure the Application

The application is pre-configured to look for AraberT at `\data\embeddings\arabert`. If your model is located elsewhere, modify the `EMBEDDING_MODEL_PATH` in `app/config.py`.

### 4. Start Ollama

Ensure that Ollama is running:

```bash
ollama serve
```

Verify that your preferred LLM model (default: `mistral:latest`) is downloaded:

```bash
ollama list
```

If not, download it:

```bash
ollama pull mistral:latest
```

### 5. Start the Application

Launch the Streamlit web interface:

```bash
streamlit run app/ui/streamlit_app.py
```

The application should now be available at `http://localhost:8501`.

## Working with Arabic Documents

### Document Processing

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

1. Check that the path in `config.py` matches your actual model location
2. Verify that the model directory contains all necessary files
3. Check the application logs for specific errors

### Out of Memory Errors

If you encounter memory issues when processing documents:

1. Reduce `EMBEDDING_BATCH_SIZE` in `config.py` (default: 16)
2. Process smaller documents or reduce the chunk size
3. Use a GPU if available (the system automatically detects and uses CUDA if available)

### Slow Embedding Generation

If embedding generation is slow:

1. Consider using a smaller AraberT model if available
2. Reduce the document chunk size to process smaller pieces of text
3. If you have a GPU, ensure PyTorch is correctly detecting and using it

## Advanced Configuration

You can tune the system by modifying parameters in `app/config.py`:

- `CHUNK_SIZE`: Size of document chunks (default: 1000 characters)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 200 characters)
- `EMBEDDING_BATCH_SIZE`: Number of chunks to embed at once (default: 16)
- `TOP_K_RETRIEVAL`: Number of document chunks to retrieve (default: 5)
- `HYBRID_ALPHA`: Balance between semantic and keyword search (default: 0.5)
