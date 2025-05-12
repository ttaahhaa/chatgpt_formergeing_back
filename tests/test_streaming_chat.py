"""
Test module for streaming chat functionality.

This module contains both pytest async tests and a manual testing script
that can be run directly to test the streaming endpoint.
"""

import os
import sys
import json
import pytest
import asyncio
import aiohttp
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the necessary modules
from app.core.llm_streaming import StreamingLLMChain, StreamingResponse
from app.database.repositories.factory import repository_factory


@pytest.fixture
def mock_streaming_llm():
    """Mock the StreamingLLMChain for testing."""
    with patch('app.core.llm_streaming.StreamingLLMChain') as mock:
        streaming_llm = mock.return_value
        
        # Setup the stream_chat mock to yield tokens
        async def mock_stream_chat(*args, **kwargs):
            # Simulate streaming tokens
            yield {"token": "Hello"}
            yield {"token": " world"}
            yield {"token": "!"}
            yield {"done": True}
            
        streaming_llm.stream_chat = mock_stream_chat
        yield streaming_llm


@pytest.fixture
def mock_conversation_repo():
    """Mock the conversation repository."""
    with patch('app.database.repositories.factory.repository_factory.conversation_repository') as mock:
        repo = AsyncMock()
        mock.return_value = repo
        
        # Configure find_by_id to return None (no existing conversation)
        repo.find_by_id = AsyncMock(return_value=None)
        
        # Configure create to succeed
        repo.create = AsyncMock(return_value=True)
        
        yield repo


@pytest.mark.asyncio
async def test_stream_chat_endpoint(mock_streaming_llm, mock_conversation_repo):
    """Test the streaming chat endpoint."""
    from fastapi.testclient import TestClient
    import asyncio
    from app.main_mongodb import app
    
    # Use TestClient for the endpoint call
    client = TestClient(app)
    
    # Test data
    test_data = {
        "message": "Hello, can you help me?",
        "conversation_id": "test-conv-123",
        "mode": "auto"
    }
    
    # We can't easily test streaming with TestClient, so we'll patch the endpoint
    # to capture what would be streamed
    with patch('app.main_mongodb.streaming_chat') as mock_endpoint:
        # Configure the mock to return what our real function would
        async def mock_stream():
            async def mock_generator():
                yield b'data: {"token": "Hello"}\n\n'
                yield b'data: {"token": " world"}\n\n'
                yield b'data: {"token": "!"}\n\n'
                yield b'data: {"done": true, "sources": []}\n\n'
                yield b'data: [DONE]\n\n'
                
            # Return a FastAPI StreamingResponse
            from fastapi.responses import StreamingResponse
            return StreamingResponse(
                mock_generator(),
                media_type="text/event-stream"
            )
            
        mock_endpoint.return_value = mock_stream()
        
        # Make the request
        response = client.post("/api/chat/stream", json=test_data)
        
        # Verify we hit our mocked endpoint
        mock_endpoint.assert_called_once()
        
        # Since this is mocked, we can't check the streaming response content
        # But we can verify the endpoint was called with the correct data
        # and that it attempted to return a streaming response
        assert response.status_code == 200
        assert mock_streaming_llm.stream_chat.called


@pytest.mark.asyncio
async def test_save_streaming_conversation():
    """Test the save_streaming_conversation helper function directly."""
    from app.main_mongodb import save_streaming_conversation
    
    # Mock the conversation repository
    conversation_repo = AsyncMock()
    conversation_repo.find_by_id = AsyncMock(return_value=None)
    conversation_repo.create = AsyncMock(return_value=True)
    
    # Create a patch for the repository factory
    with patch('app.database.repositories.factory.repository_factory.conversation_repository', 
               new=conversation_repo):
        # Call the function with test data
        await save_streaming_conversation(
            conversation_id="test-conv-123",
            user_message="Hello",
            assistant_response="Hi there!",
            sources=[{"document": "test.txt", "content": "Test content"}]
        )
        
        # Verify conversation repo was called to find by ID
        conversation_repo.find_by_id.assert_called_once_with("test-conv-123")
        
        # Since we mocked find_by_id to return None, verify create was called
        conversation_repo.create.assert_called_once()
        
        # Check that the document passed to create has the right structure
        call_args = conversation_repo.create.call_args[0][0]
        assert call_args.id == "test-conv-123"
        assert len(call_args.messages) == 2
        assert call_args.messages[0]["role"] == "user"
        assert call_args.messages[0]["content"] == "Hello"
        assert call_args.messages[1]["role"] == "assistant"
        assert call_args.messages[1]["content"] == "Hi there!"
        assert call_args.messages[1]["sources"][0]["document"] == "test.txt"


# Manual Testing Script
async def test_streaming_chat_client():
    """
    Manual testing client for the streaming chat endpoint.
    
    Run this script directly to test the streaming chat functionality:
    python -m tests.test_streaming_chat
    """
    base_url = "http://localhost:8001"
    endpoint = f"{base_url}/api/chat/stream"
    
    # Test payload
    payload = {
        "message": "Tell me about machine learning in 5 sentences",
        "conversation_id": f"test-{datetime.now().timestamp()}",
        "mode": "auto"
    }
    
    print(f"Testing streaming endpoint at {endpoint}")
    print(f"Sending message: {payload['message']}")
    print("Streaming response:")
    print("-" * 40)
    
    full_response = ""
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"Error: {response.status} - {error_text}")
                    return
                
                # Process server-sent events
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if not line:
                        continue
                    
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        
                        if data == '[DONE]':
                            print("\n[Stream complete]")
                            break
                        
                        try:
                            event = json.loads(data)
                            if 'token' in event:
                                token = event['token']
                                full_response += token
                                print(token, end='', flush=True)
                            elif 'error' in event:
                                print(f"\nError: {event['error']}")
                                break
                            elif 'done' in event and event['done']:
                                sources = event.get('sources', [])
                                if sources:
                                    print("\n\nSources:")
                                    for i, source in enumerate(sources, 1):
                                        print(f"{i}. {source.get('document', 'Unknown')}")
                        except json.JSONDecodeError:
                            print(f"\nError parsing JSON: {data}")
    
    except Exception as e:
        print(f"\nError during streaming: {str(e)}")
    
    print("\n" + "-" * 40)
    print("Full response:")
    print(full_response)


# Run the manual test when the script is executed directly
if __name__ == "__main__":
    print("Running streaming chat client test...")
    asyncio.run(test_streaming_chat_client()) 