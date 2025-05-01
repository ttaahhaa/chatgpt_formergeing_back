# app/utils/conversation_utils.py

import os
import shutil
import tempfile
from pathlib import Path
import json

CONVERSATION_DIR = Path(tempfile.gettempdir()) / "conversations"

def clear_context():
    try:
        if CONVERSATION_DIR.exists():
            shutil.rmtree(CONVERSATION_DIR)
        CONVERSATION_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        return False

def create_new_conversation(conversation_id: str):
    try:
        CONVERSATION_DIR.mkdir(parents=True, exist_ok=True)
        conversation_path = CONVERSATION_DIR / f"{conversation_id}.json"
        conversation_path.write_text('{"messages": [], "preview": ""}', encoding='utf-8')
    except Exception as e:
        raise RuntimeError(f"Failed to create conversation: {e}")

def list_conversations():
    """List all saved conversations with improved field handling."""
    if not CONVERSATION_DIR.exists():
        return []

    conversations = []
    for file in CONVERSATION_DIR.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Check for different field names
            messages = data.get("messages", data.get("history", []))
            
            # Calculate message count if not present
            message_count = data.get("messageCount", len(messages))
            
            # Use ISO format for last_updated if not present
            last_updated = data.get("last_updated", "")
            if not last_updated:
                import datetime
                last_updated = datetime.datetime.now().isoformat()
                
            # Use placeholder preview if empty
            preview = data.get("preview", "New Conversation")
            if not preview:
                preview = "New Conversation"
                
            conversations.append({
                "id": file.stem,
                "preview": preview,
                "lastUpdated": last_updated,
                "messageCount": message_count,
            })
        except Exception as e:
            print(f"Error loading conversation {file}: {str(e)}")
            # Include the conversation with error info to avoid hiding it
            conversations.append({
                "id": file.stem,
                "preview": "Error loading conversation",
                "lastUpdated": "",
                "messageCount": 0,
            })

    # Sort by last updated, with newest first
    return sorted(conversations, key=lambda c: c["lastUpdated"] if c["lastUpdated"] else "", reverse=True)

def save_conversation(data: dict):
    CONVERSATION_DIR.mkdir(parents=True, exist_ok=True)
    conv_id = data.get("conversation_id")
    if not conv_id:
        raise ValueError("conversation_id is required")

    path = CONVERSATION_DIR / f"{conv_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

