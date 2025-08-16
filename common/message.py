"""
Common message handling for the chat application.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from .config import MessageType
from .protocol import ChatProtocol


class ChatMessage:
    """Represents a chat message with all necessary metadata."""
    
    def __init__(self, msg_type: str, sender: str, content: str, timestamp: str):
        self.type = msg_type
        self.sender = sender
        self.content = content
        self.timestamp = timestamp
        self.formatted_time = self._parse_timestamp()
    
    def _parse_timestamp(self) -> str:
        """Parse the timestamp and format it for display."""
        try:
            dt = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            return dt.strftime("%H:%M:%S")
        except:
            return datetime.now().strftime("%H:%M:%S")
    
    @staticmethod
    def create(msg_type: MessageType, content: str, sender: str = "SERVER") -> str:
        """Create a formatted message string."""
        return ChatProtocol.create_message(msg_type, content, sender)
    
    @staticmethod
    def parse(message_str: str) -> Optional[Dict[str, Any]]:
        """Parse JSON message from server."""
        return ChatProtocol.parse_message(message_str)