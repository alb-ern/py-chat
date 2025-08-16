"""
Protocol definitions for the chat application.
This module defines the message format and communication protocol.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from .config import MessageType


class ChatProtocol:
    """Handles the chat protocol for message formatting and parsing."""
    
    @staticmethod
    def create_message(msg_type: MessageType, content: str, sender: str = "SERVER") -> str:
        """Create a formatted message string according to the protocol."""
        message = {
            "type": msg_type.value,
            "sender": sender,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(message)
    
    @staticmethod
    def parse_message(message_str: str) -> Optional[Dict[str, Any]]:
        """Parse a message string according to the protocol."""
        try:
            return json.loads(message_str)
        except json.JSONDecodeError:
            logging.warning(f"Failed to parse message: {message_str}")
            return None
    
    @staticmethod
    def validate_message(message: Dict[str, Any]) -> bool:
        """Validate that a message has the required fields."""
        required_fields = ["type", "sender", "content", "timestamp"]
        return all(field in message for field in required_fields) and \
               message["type"] in [t.value for t in MessageType]
    
    @staticmethod
    def create_error_message(content: str) -> str:
        """Create an error message."""
        return ChatProtocol.create_message(MessageType.ERROR, content)
    
    @staticmethod
    def create_system_message(content: str) -> str:
        """Create a system message."""
        return ChatProtocol.create_message(MessageType.SYSTEM, content)