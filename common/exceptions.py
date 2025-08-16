"""
Custom exceptions for the chat application.
"""
class ChatApplicationError(Exception):
    """Base exception for chat application errors."""
    pass


class ConnectionError(ChatApplicationError):
    """Raised when there is a connection error."""
    pass


class AuthenticationError(ChatApplicationError):
    """Raised when authentication fails."""
    pass


class MessageError(ChatApplicationError):
    """Raised when there is an error with message handling."""
    pass


class ProtocolError(ChatApplicationError):
    """Raised when there is a protocol violation."""
    pass


class ConfigurationError(ChatApplicationError):
    """Raised when there is a configuration error."""
    pass