"""
Common configuration for the chat application.
"""
from enum import Enum


class Config:
    """Configuration settings shared between client and server."""
    HOST = '127.0.0.1'
    SERVER_HOST = '127.0.0.1'
    SERVER_PORT = 12345
    PORT = 12345
    MESSAGE_SIZE_LIMIT = 1024
    RECONNECT_ATTEMPTS = 5
    RECONNECT_DELAY = 3
    CONNECTION_TIMEOUT = 10
    DATABASE_FILE = 'chat_server.db'
    MAX_CLIENTS = 50
    RATE_LIMIT_MESSAGES = 10
    RATE_LIMIT_WINDOW = 60
    MESSAGE_HISTORY_LIMIT = 100


class MessageType(Enum):
    """Message types used in the chat application."""
    CHAT = "chat"
    JOIN = "join"
    LEAVE = "leave"
    PRIVATE = "private"
    SYSTEM = "system"
    ERROR = "error"
    USER_LIST = "user_list"