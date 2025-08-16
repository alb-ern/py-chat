"""
Client-side networking components for the TUI chat application.
"""
import socket
import threading
import json
import logging
import sys
import os
from typing import Optional, Dict, Any
from datetime import datetime

# Add the parent directory to the path to import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.config import Config, MessageType
from common.message import ChatMessage
from common.exceptions import ConnectionError, AuthenticationError


class NetworkManager:
    """Handles all network communication for the client."""
    
    def __init__(self, client):
        self.client = client
        self.socket: Optional[socket.socket] = None
        self.receive_thread: Optional[threading.Thread] = None
    
    def connect_to_server(self) -> bool:
        """Connect to the chat server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(Config.CONNECTION_TIMEOUT)
            self.socket.connect((Config.SERVER_HOST, Config.SERVER_PORT))
            
            # Wait for nickname request
            response = self.socket.recv(Config.MESSAGE_SIZE_LIMIT).decode('utf-8')
            if response != "NICK":
                return False
            
            # Send nickname
            self.socket.send(self.client.nickname.encode('utf-8'))
            
            # Wait for response
            response = self.socket.recv(Config.MESSAGE_SIZE_LIMIT).decode('utf-8')
            message = ChatMessage.parse(response)
            
            if message and message.get("type") == "error":
                return False
            
            self.client.connected = True
            return True
            
        except socket.timeout:
            logging.error("Connection timed out")
            return False
        except socket.gaierror as e:
            logging.error(f"Address resolution failed: {e}")
            return False
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            return False
    
    def send_message(self, message: str):
        """Send message to server."""
        if not self.client.connected or not self.socket:
            return
        
        try:
            self.socket.send(message.encode('utf-8'))
            
            # Display own message immediately for better UX
            if not message.startswith('/'):
                own_message = {
                    "type": "chat",
                    "sender": self.client.nickname,
                    "content": message,
                    "timestamp": datetime.now().isoformat()
                }
                self.client.add_message(own_message)
            
        except socket.timeout:
            logging.error("Send message timed out")
            self.client.connected = False
        except BrokenPipeError:
            logging.error("Connection broken")
            self.client.connected = False
        except Exception as e:
            logging.error(f"Error sending message: {e}")
            self.client.connected = False
    
    def request_user_list(self):
        """Request current user list from server."""
        self.send_message("/list")
    
    def handle_server_messages(self):
        """Handle messages from server."""
        while self.client.running and self.client.connected:
            try:
                if not self.socket:
                    break
                
                self.socket.settimeout(1.0)
                message_data = self.socket.recv(Config.MESSAGE_SIZE_LIMIT)
                
                if not message_data:
                    self.client.connected = False
                    break
                
                message_str = message_data.decode('utf-8')
                message = ChatMessage.parse(message_str)
                
                if message:
                    self.client.add_message(message)
                
            except socket.timeout:
                continue
            except ConnectionResetError:
                logging.info("Connection reset by server")
                self.client.connected = False
                break
            except Exception as e:
                logging.error(f"Error receiving message: {e}")
                self.client.connected = False
                break
    
    def disconnect(self):
        """Disconnect from server."""
        self.client.connected = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass