"""
API routes package.
Exports all route modules for easy importing.
"""

from . import auth, chat, documents, conversations, system, admin

__all__ = ["auth", "chat", "documents", "conversations", "system", "admin"]