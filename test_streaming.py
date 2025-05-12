"""
Simple test script to verify the streaming chat functionality.
"""

import asyncio
import json
import aiohttp
import sys
from datetime import datetime

async def test_streaming():
    base_url = "http://localhost:8001"
    endpoint = f"{base_url}/api/chat/stream"
    
    # Test payload
    payload = {
        "message": "Tell me about machine learning in 3 sentences",
        "conversation_id": f"test-{datetime.now().timestamp()}",
        "mode": "auto"
    }
    
    print(f"\nTesting streaming endpoint at {endpoint}")
    print(f"Sending message: {payload['message']}")
    print("\nStreaming response:")
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

if __name__ == "__main__":
    print("Testing streaming chat...")
    asyncio.run(test_streaming()) 