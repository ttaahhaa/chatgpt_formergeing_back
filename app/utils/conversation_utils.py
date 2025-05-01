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
    if not CONVERSATION_DIR.exists():
        return []

    conversations = []
    for file in CONVERSATION_DIR.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
        conversations.append({
            "id": file.stem,
            "preview": data.get("preview", "New Conversation"),
            "lastUpdated": data.get("last_updated", ""),
            "messageCount": len(data.get("history", [])),
        })

    return sorted(conversations, key=lambda c: c["lastUpdated"], reverse=True)

def save_conversation(data: dict):
    CONVERSATION_DIR.mkdir(parents=True, exist_ok=True)
    conv_id = data.get("conversation_id")
    if not conv_id:
        raise ValueError("conversation_id is required")

    path = CONVERSATION_DIR / f"{conv_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)