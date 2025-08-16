"""
Utility functions for the chat application.
"""
import re
from typing import List, Tuple, Any


def validate_nickname(nickname: str) -> Tuple[bool, str]:
    """
    Validate a nickname.
    
    Args:
        nickname: The nickname to validate
        
    Returns:
        A tuple of (is_valid, error_message)
    """
    if not nickname or len(nickname.strip()) == 0:
        return False, "Nickname cannot be empty"
    
    nickname = nickname.strip()
    if len(nickname) > 20:
        return False, "Nickname too long (max 20 characters)"
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', nickname):
        return False, "Nickname can only contain letters, numbers, hyphens, and underscores"
    
    return True, nickname


def format_uptime(seconds: int) -> str:
    """
    Format uptime in seconds to a human-readable string.
    
    Args:
        seconds: Uptime in seconds
        
    Returns:
        A formatted uptime string
    """
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m {secs}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.
    
    Args:
        text: The text to truncate
        max_length: The maximum length
        suffix: The suffix to append if truncated
        
    Returns:
        The truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def safe_int_conversion(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to an integer.
    
    Args:
        value: The value to convert
        default: The default value if conversion fails
        
    Returns:
        The converted integer or default value
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default