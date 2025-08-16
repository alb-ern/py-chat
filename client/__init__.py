"""
Main client module for the TUI chat application.
"""
import threading
import logging
import time
import sys
import os
import socket
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
import curses
from curses import wrapper

# Add the parent directory to the path to import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import Config, MessageType
from common.message import ChatMessage
from client.ui import UIComponents
from client.network import NetworkManager


class TUIChatClient:
    """Main TUI chat client class."""
    
    def __init__(self):
        self.socket: Optional[socket.socket] = None
        self.nickname: str = ""
        self.connected = False
        self.running = False
        
        # UI State
        self.messages: List[ChatMessage] = []
        self.current_input = ""
        self.input_cursor_pos = 0
        self.scroll_offset = 0
        self.users_online: List[str] = []
        self.show_users = True
        
        # Curses windows
        self.stdscr = None
        self.chat_win = None
        self.input_win = None
        self.status_win = None
        self.users_win = None
        
        # Components
        self.ui = UIComponents(self)
        self.network = NetworkManager(self)
        
        # Threading
        self.receive_thread: Optional[threading.Thread] = None
        self.ui_update_thread: Optional[threading.Thread] = None
        self.user_list_update_thread: Optional[threading.Thread] = None
        
        # Setup logging (to file only to avoid interfering with TUI)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler('chat_client.log')]
        )
        self.logger = logging.getLogger(__name__)
    
    def add_message(self, message: Dict[str, Any]):
        """Add a message to the chat display."""
        chat_msg = ChatMessage(
            message.get("type", "chat"),
            message.get("sender", "unknown"),
            message.get("content", ""),
            message.get("timestamp", datetime.now().isoformat())
        )
        
        # Update users list if it's a user_list message
        if chat_msg.type == MessageType.USER_LIST.value:
            try:
                self.users_online = json.loads(chat_msg.content)
            except:
                pass
            # Don't add USER_LIST messages to chat display
            return
        # Update users list if it's a join/leave message
        elif chat_msg.type == MessageType.JOIN.value:
            user = chat_msg.content.split(" ")[0] if " joined" in chat_msg.content else None
            if user and user not in self.users_online:
                self.users_online.append(user)
        elif chat_msg.type == MessageType.LEAVE.value:
            user = chat_msg.content.split(" ")[0] if " left" in chat_msg.content else None
            if user and user in self.users_online:
                self.users_online.remove(user)
        
        # Add message to chat display (excluding USER_LIST messages)
        self.messages.append(chat_msg)
        
        # Keep message history limited
        if len(self.messages) > 1000:
            self.messages = self.messages[-500:]  # Keep last 500 messages
    
    def handle_input(self, key):
        """Handle keyboard input."""
        if key == curses.KEY_ENTER or key == ord('\n') or key == ord('\r'):
            # Send message
            if self.current_input.strip():
                self.network.send_message(self.current_input.strip())
                self.current_input = ""
                self.input_cursor_pos = 0
        
        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            # Backspace
            if self.input_cursor_pos > 0:
                self.current_input = (self.current_input[:self.input_cursor_pos-1] + 
                                    self.current_input[self.input_cursor_pos:])
                self.input_cursor_pos -= 1
        
        elif key == curses.KEY_DC:  # Delete key
            if self.input_cursor_pos < len(self.current_input):
                self.current_input = (self.current_input[:self.input_cursor_pos] + 
                                    self.current_input[self.input_cursor_pos+1:])
        
        elif key == curses.KEY_LEFT:
            if self.input_cursor_pos > 0:
                self.input_cursor_pos -= 1
        
        elif key == curses.KEY_RIGHT:
            if self.input_cursor_pos < len(self.current_input):
                self.input_cursor_pos += 1
        
        elif key == curses.KEY_HOME:
            self.input_cursor_pos = 0
        
        elif key == curses.KEY_END:
            self.input_cursor_pos = len(self.current_input)
        
        elif key == curses.KEY_UP:
            # Scroll up in chat
            if self.scroll_offset > 0:
                self.scroll_offset -= 1
        
        elif key == curses.KEY_DOWN:
            # Scroll down in chat
            if self.scroll_offset < 0:
                self.scroll_offset += 1
        
        elif key == curses.KEY_F1:
            # Show help
            self.ui.show_help_dialog(self.stdscr)
        
        elif key == curses.KEY_F2:
            # Toggle users panel
            self.show_users = not self.show_users
            self.ui.setup_windows(self.stdscr)
        
        elif key == 27:  # ESC key
            self.network.disconnect()
            return False
        
        elif 32 <= key <= 126:  # Printable characters
            self.current_input = (self.current_input[:self.input_cursor_pos] + 
                                chr(key) + self.current_input[self.input_cursor_pos:])
            self.input_cursor_pos += 1
        
        return True
    
    def get_nickname(self):
        """Get nickname from user using simple input."""
        curses.endwin()  # Temporarily exit curses mode
        
        print("=== Chat Client ===")
        while True:
            nickname = input("Enter your nickname: ").strip()
            if nickname and len(nickname) <= 20 and nickname.replace('_', '').replace('-', '').isalnum():
                self.nickname = nickname
                break
            print("Invalid nickname. Use only letters, numbers, hyphens, and underscores (max 20 chars)")
        
        # Reinitialize curses
        self.stdscr = curses.initscr()
        self.ui.setup_colors(self.stdscr)
        self.ui.setup_windows(self.stdscr)
    
    def start_user_list_updates(self):
        """Start periodic user list updates."""
        def update_user_list():
            while self.running and self.connected:
                try:
                    # Request user list every 10 seconds
                    time.sleep(10)
                    if self.connected:
                        self.network.request_user_list()
                except Exception as e:
                    self.logger.error(f"Error in user list update thread: {e}")
                    break
        
        self.user_list_update_thread = threading.Thread(target=update_user_list, daemon=True)
        self.user_list_update_thread.start()
    
    def run_ui_loop(self):
        """Main UI loop."""
        while self.running:
            try:
                # Refresh UI
                self.ui.refresh_ui()
                
                # Handle input with timeout
                self.stdscr.timeout(100)  # 100ms timeout
                key = self.stdscr.getch()
                
                if key != -1:  # Key was pressed
                    if not self.handle_input(key):
                        break
                
                # Check connection status
                if not self.connected and self.running:
                    # Add disconnection message
                    self.add_message({
                        "type": "error",
                        "sender": "SYSTEM",
                        "content": "Disconnected from server",
                        "timestamp": datetime.now().isoformat()
                    })
                    time.sleep(3)  # Show message for 3 seconds
                    break
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"UI loop error: {e}")
    
    def start_client(self, stdscr):
        """Start the TUI chat client."""
        self.stdscr = stdscr
        self.running = True
        
        # Setup curses
        curses.curs_set(1)  # Show cursor
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        
        self.ui.setup_colors(stdscr)
        
        # Get nickname
        self.get_nickname()
        
        # Show connecting message
        self.add_message({
            "type": "system",
            "sender": "SYSTEM",
            "content": f"Connecting to {Config.SERVER_HOST}:{Config.SERVER_PORT}...",
            "timestamp": datetime.now().isoformat()
        })
        self.ui.refresh_ui()
        
        # Connect to server
        if not self.network.connect_to_server():
            self.add_message({
                "type": "error",
                "sender": "SYSTEM",
                "content": "Failed to connect to server",
                "timestamp": datetime.now().isoformat()
            })
            self.ui.refresh_ui()
            time.sleep(3)
            return
        
        # Add welcome message
        self.add_message({
            "type": "system",
            "sender": "SYSTEM",
            "content": "Connected! Type /help for commands or start chatting. Press F1 for UI help.",
            "timestamp": datetime.now().isoformat()
        })
        
        # Start periodic user list updates
        self.start_user_list_updates()
        
        # Start server message handler
        self.receive_thread = threading.Thread(target=self.network.handle_server_messages, daemon=True)
        self.receive_thread.start()
        
        # Run UI loop
        self.run_ui_loop()
        
        # Cleanup
        self.network.disconnect()


def main():
    """Main entry point."""
    client = TUIChatClient()
    
    try:
        wrapper(client.start_client)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Goodbye!")


if __name__ == "__main__":
    main()