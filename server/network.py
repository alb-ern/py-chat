"""
Server-side networking components for the chat application.
"""
import socket
import threading
import json
import logging
import sys
import os
from typing import Optional, Callable
from datetime import datetime

# Add the parent directory to the path to import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.config import Config, MessageType
from common.message import ChatMessage
from common.exceptions import ConnectionError


class NetworkManager:
    """Handles all network communication for the server."""
    
    def __init__(self, server):
        self.server = server
        self.server_socket: Optional[socket.socket] = None
    
    def start_listening(self, host: str, port: int, max_clients: int):
        """Start listening for client connections."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((host, port))
            self.server_socket.listen(max_clients)
            return True
        except socket.error as e:
            logging.error(f"Socket error while starting listening: {e}")
            return False
        except Exception as e:
            logging.error(f"Failed to start listening: {e}")
            return False
    
    def accept_connection(self, timeout: float = 1.0):
        """Accept a new client connection."""
        try:
            if self.server_socket:
                self.server_socket.settimeout(timeout)
                client_socket, address = self.server_socket.accept()
                return client_socket, address
        except socket.timeout:
            return None, None
        except socket.error as e:
            if self.server.running:
                logging.error(f"Socket error accepting connection: {e}")
        except Exception as e:
            if self.server.running:
                logging.error(f"Error accepting connection: {e}")
        return None, None
    
    def send_message(self, client_socket: socket.socket, message: str) -> bool:
        """Send a message to a specific client."""
        try:
            client_socket.send(message.encode('utf-8'))
            return True
        except (ConnectionResetError, BrokenPipeError):
            return False
        except socket.error as e:
            logging.error(f"Socket error sending message: {e}")
            return False
        except Exception as e:
            logging.error(f"Error sending message: {e}")
            return False
    
    def broadcast(self, message: str, exclude_fd: Optional[int] = None):
        """Send message to all connected clients except excluded one."""
        disconnected = []
        sent_count = 0
        
        for fd, client in self.server.client_manager.get_all_clients().items():
            if exclude_fd and fd == exclude_fd:
                continue
            if self.send_message(client.socket, message):
                sent_count += 1
            else:
                disconnected.append(fd)
        
        # Remove disconnected clients
        for fd in disconnected:
            self.server.remove_client(fd)
        
        self.server.stats.messages_sent += sent_count
    
    def close(self):
        """Close the server socket."""
        if self.server_socket:
            try:
                self.server_socket.close()
            except socket.error as e:
                logging.error(f"Socket error closing server socket: {e}")
            except Exception as e:
                logging.error(f"Error closing server socket: {e}")