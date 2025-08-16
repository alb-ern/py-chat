"""
Server-side client management for the chat application.
"""
import socket
import threading
import time
import sys
import os
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Optional

# Add the parent directory to the path to import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.config import MessageType


@dataclass
class Client:
    """Represents a connected client."""
    socket: socket.socket
    nickname: str
    address: tuple
    join_time: datetime
    user_id: int
    last_message_time: float = 0
    message_count: int = 0
    
    def reset_rate_limit(self):
        """Reset rate limiting counters."""
        self.message_count = 0
        self.last_message_time = time.time()


class ClientManager:
    """Manages all connected clients."""
    
    def __init__(self):
        self.clients: Dict[int, Client] = {}
        self.nicknames: set = set()
    
    def add_client(self, client_fd: int, client: Client):
        """Add a new client."""
        self.clients[client_fd] = client
        self.nicknames.add(client.nickname)
    
    def remove_client(self, client_fd: int) -> Optional[Client]:
        """Remove a client and return it."""
        if client_fd in self.clients:
            client = self.clients[client_fd]
            del self.clients[client_fd]
            self.nicknames.discard(client.nickname)
            return client
        return None
    
    def get_client_by_fd(self, client_fd: int) -> Optional[Client]:
        """Get a client by file descriptor."""
        return self.clients.get(client_fd)
    
    def get_client_by_nickname(self, nickname: str) -> Optional[Client]:
        """Get a client by nickname."""
        for client in self.clients.values():
            if client.nickname.lower() == nickname.lower():
                return client
        return None
    
    def get_all_clients(self) -> Dict[int, Client]:
        """Get all clients."""
        return self.clients
    
    def get_nicknames(self) -> set:
        """Get all nicknames."""
        return self.nicknames
    
    def get_client_count(self) -> int:
        """Get the number of connected clients."""
        return len(self.clients)