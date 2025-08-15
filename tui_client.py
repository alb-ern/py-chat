import threading
import socket
import json
import logging
import time
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import curses
from curses import wrapper
import textwrap

# Configuration
class Config:
    SERVER_HOST = '127.0.0.1'
    SERVER_PORT = 12345
    MESSAGE_SIZE_LIMIT = 1024
    RECONNECT_ATTEMPTS = 5
    RECONNECT_DELAY = 3
    CONNECTION_TIMEOUT = 10

class MessageType(Enum):
    CHAT = "chat"
    JOIN = "join"
    LEAVE = "leave"
    PRIVATE = "private"
    SYSTEM = "system"
    ERROR = "error"

class Colors:
    # ANSI color codes for fallback
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Text colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_BLUE = '\033[44m'
    BG_GREEN = '\033[42m'

class ChatMessage:
    def __init__(self, msg_type: str, sender: str, content: str, timestamp: str):
        self.type = msg_type
        self.sender = sender
        self.content = content
        self.timestamp = timestamp
        self.formatted_time = self._parse_timestamp()
    
    def _parse_timestamp(self) -> str:
        try:
            dt = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            return dt.strftime("%H:%M:%S")
        except:
            return datetime.now().strftime("%H:%M:%S")

class TUIChatClient:
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
        
        # Colors (curses color pairs)
        self.color_pairs = {}
        
        # Threading
        self.receive_thread: Optional[threading.Thread] = None
        self.ui_update_thread: Optional[threading.Thread] = None
        
        # Setup logging (to file only to avoid interfering with TUI)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler('chat_client.log')]
        )
        self.logger = logging.getLogger(__name__)

    def setup_colors(self):
        """Initialize curses color pairs"""
        if not curses.has_colors():
            return
            
        curses.start_color()
        curses.use_default_colors()
        
        # Define color pairs
        color_definitions = {
            'default': (curses.COLOR_WHITE, -1),
            'system': (curses.COLOR_YELLOW, -1),
            'error': (curses.COLOR_RED, -1),
            'success': (curses.COLOR_GREEN, -1),
            'private': (curses.COLOR_MAGENTA, -1),
            'join': (curses.COLOR_CYAN, -1),
            'leave': (curses.COLOR_BLUE, -1),
            'own_message': (curses.COLOR_GREEN, -1),
            'timestamp': (curses.COLOR_WHITE, -1),
            'username': (curses.COLOR_CYAN, -1),
            'status_bar': (curses.COLOR_BLACK, curses.COLOR_WHITE),
            'input_box': (curses.COLOR_WHITE, curses.COLOR_BLUE),
            'users_panel': (curses.COLOR_YELLOW, -1)
        }
        
        for i, (name, (fg, bg)) in enumerate(color_definitions.items(), 1):
            try:
                curses.init_pair(i, fg, bg)
                self.color_pairs[name] = curses.color_pair(i)
            except:
                self.color_pairs[name] = curses.A_NORMAL

    def setup_windows(self):
        """Setup curses windows layout"""
        height, width = self.stdscr.getmaxyx()
        
        # Calculate window dimensions
        users_width = 20 if self.show_users else 0
        chat_width = width - users_width
        chat_height = height - 3  # Leave space for status and input
        
        # Create windows
        self.chat_win = curses.newwin(chat_height, chat_width, 0, 0)
        self.status_win = curses.newwin(1, width, chat_height, 0)
        self.input_win = curses.newwin(2, width, chat_height + 1, 0)
        
        if self.show_users and users_width > 0:
            self.users_win = curses.newwin(chat_height, users_width, 0, chat_width)
        
        # Configure windows
        self.chat_win.scrollok(True)
        self.input_win.box()
        if self.users_win:
            self.users_win.box()
        
        # Set colors
        self.status_win.bkgd(' ', self.color_pairs.get('status_bar', curses.A_REVERSE))

    def draw_status_bar(self):
        """Draw the status bar"""
        if not self.status_win:
            return
            
        height, width = self.status_win.getmaxyx()
        self.status_win.clear()
        
        # Connection status
        status = "Connected" if self.connected else "Disconnected"
        status_color = self.color_pairs.get('success' if self.connected else 'error', curses.A_NORMAL)
        
        # Create status text
        left_text = f" {self.nickname} | {status}"
        right_text = f"Users: {len(self.users_online)} | Press F1 for help "
        
        # Draw status text
        self.status_win.addstr(0, 0, left_text[:width-1], status_color)
        
        # Right-align text
        if len(right_text) < width - len(left_text):
            self.status_win.addstr(0, width - len(right_text) - 1, right_text, 
                                 self.color_pairs.get('default', curses.A_NORMAL))
        
        self.status_win.refresh()

    def draw_users_panel(self):
        """Draw the users panel"""
        if not self.users_win or not self.show_users:
            return
            
        height, width = self.users_win.getmaxyx()
        self.users_win.clear()
        self.users_win.box()
        
        # Title
        title = "Users Online"
        self.users_win.addstr(1, 2, title, self.color_pairs.get('users_panel', curses.A_BOLD))
        self.users_win.addstr(2, 2, "─" * (width - 4))
        
        # User list
        for i, user in enumerate(self.users_online[:height - 5]):
            color = self.color_pairs.get('own_message' if user == self.nickname else 'username', 
                                       curses.A_NORMAL)
            indicator = "● " if user == self.nickname else "○ "
            user_text = f"{indicator}{user}"
            
            if len(user_text) > width - 4:
                user_text = user_text[:width - 7] + "..."
            
            self.users_win.addstr(3 + i, 2, user_text, color)
        
        # Show count if truncated
        if len(self.users_online) > height - 5:
            self.users_win.addstr(height - 2, 2, f"...and {len(self.users_online) - (height - 5)} more", 
                                self.color_pairs.get('system', curses.A_DIM))
        
        self.users_win.refresh()

    def draw_chat_messages(self):
        """Draw chat messages"""
        if not self.chat_win:
            return
            
        height, width = self.chat_win.getmaxyx()
        self.chat_win.clear()
        
        # Calculate which messages to show
        visible_messages = self.messages[-height + self.scroll_offset:] if self.messages else []
        
        line = 0
        for msg in visible_messages:
            if line >= height:
                break
                
            # Format message based on type
            formatted_lines = self.format_message_for_display(msg, width)
            
            for formatted_line in formatted_lines:
                if line >= height:
                    break
                
                text, color = formatted_line
                try:
                    self.chat_win.addstr(line, 0, text[:width-1], color)
                except curses.error:
                    pass  # Ignore errors from writing at screen edges
                line += 1
        
        self.chat_win.refresh()

    def format_message_for_display(self, msg: ChatMessage, width: int) -> List[tuple]:
        """Format a message for display with colors"""
        lines = []
        
        # Get appropriate colors
        if msg.type == MessageType.SYSTEM.value:
            color = self.color_pairs.get('system', curses.A_NORMAL)
            prefix = "● "
        elif msg.type == MessageType.ERROR.value:
            color = self.color_pairs.get('error', curses.A_NORMAL)
            prefix = "✗ "
        elif msg.type == MessageType.PRIVATE.value:
            color = self.color_pairs.get('private', curses.A_NORMAL)
            prefix = "🔒 "
        elif msg.type == MessageType.JOIN.value:
            color = self.color_pairs.get('join', curses.A_NORMAL)
            prefix = "→ "
        elif msg.type == MessageType.LEAVE.value:
            color = self.color_pairs.get('leave', curses.A_NORMAL)
            prefix = "← "
        else:  # Regular chat
            if msg.sender == self.nickname:
                color = self.color_pairs.get('own_message', curses.A_NORMAL)
                prefix = ""
            else:
                color = self.color_pairs.get('default', curses.A_NORMAL)
                prefix = ""
        
        # Format message text
        if msg.type in [MessageType.CHAT.value, MessageType.PRIVATE.value]:
            # Chat messages: [time] username: message
            time_part = f"[{msg.formatted_time}] "
            user_part = f"{msg.sender}: " if msg.sender != "SERVER" else ""
            message_text = f"{time_part}{user_part}{msg.content}"
        else:
            # System messages: [time] ● message
            time_part = f"[{msg.formatted_time}] "
            message_text = f"{time_part}{prefix}{msg.content}"
        
        # Wrap long messages
        wrapped_lines = textwrap.wrap(message_text, width - 1)
        if not wrapped_lines:
            wrapped_lines = [message_text]
        
        for i, line in enumerate(wrapped_lines):
            # First line gets the color, subsequent lines are dimmed
            line_color = color if i == 0 else self.color_pairs.get('default', curses.A_DIM)
            lines.append((line, line_color))
        
        return lines

    def draw_input_box(self):
        """Draw the input box"""
        if not self.input_win:
            return
            
        height, width = self.input_win.getmaxyx()
        self.input_win.clear()
        self.input_win.box()
        
        # Input prompt
        prompt = f" {self.nickname}> "
        self.input_win.addstr(1, 1, prompt, self.color_pairs.get('username', curses.A_BOLD))
        
        # Current input text
        input_start = len(prompt) + 1
        available_width = width - input_start - 2
        
        # Handle text scrolling if input is too long
        display_text = self.current_input
        cursor_display_pos = self.input_cursor_pos
        
        if len(display_text) > available_width:
            if cursor_display_pos > available_width - 5:
                # Scroll text to show cursor
                start_pos = cursor_display_pos - available_width + 5
                display_text = display_text[start_pos:]
                cursor_display_pos = cursor_display_pos - start_pos
        
        self.input_win.addstr(1, input_start, display_text[:available_width], 
                            self.color_pairs.get('default', curses.A_NORMAL))
        
        # Position cursor
        cursor_x = input_start + cursor_display_pos
        if cursor_x < width - 1:
            self.input_win.move(1, cursor_x)
        
        self.input_win.refresh()

    def refresh_ui(self):
        """Refresh all UI components"""
        try:
            self.draw_status_bar()
            self.draw_users_panel()
            self.draw_chat_messages()
            self.draw_input_box()
        except curses.error:
            pass  # Ignore curses errors during refresh

    def add_message(self, message: Dict[str, Any]):
        """Add a message to the chat display"""
        chat_msg = ChatMessage(
            message.get("type", "chat"),
            message.get("sender", "unknown"),
            message.get("content", ""),
            message.get("timestamp", datetime.now().isoformat())
        )
        
        self.messages.append(chat_msg)
        
        # Keep message history limited
        if len(self.messages) > 1000:
            self.messages = self.messages[-500:]  # Keep last 500 messages
        
        # Update users list if it's a join/leave message
        if chat_msg.type == MessageType.JOIN.value:
            user = chat_msg.content.split(" ")[0] if " joined" in chat_msg.content else None
            if user and user not in self.users_online:
                self.users_online.append(user)
        elif chat_msg.type == MessageType.LEAVE.value:
            user = chat_msg.content.split(" ")[0] if " left" in chat_msg.content else None
            if user and user in self.users_online:
                self.users_online.remove(user)

    def handle_input(self, key):
        """Handle keyboard input"""
        if key == curses.KEY_ENTER or key == ord('\n') or key == ord('\r'):
            # Send message
            if self.current_input.strip():
                self.send_message(self.current_input.strip())
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
            self.show_help_dialog()
        
        elif key == curses.KEY_F2:
            # Toggle users panel
            self.show_users = not self.show_users
            self.setup_windows()
        
        elif key == 27:  # ESC key
            self.disconnect()
            return False
        
        elif 32 <= key <= 126:  # Printable characters
            self.current_input = (self.current_input[:self.input_cursor_pos] + 
                                chr(key) + self.current_input[self.input_cursor_pos:])
            self.input_cursor_pos += 1
        
        return True

    def show_help_dialog(self):
        """Show help dialog"""
        help_text = [
            "=== CHAT CLIENT HELP ===",
            "",
            "Navigation:",
            "  ↑/↓ Arrow Keys - Scroll chat history",
            "  Enter - Send message",
            "  Esc - Quit application",
            "",
            "Function Keys:",
            "  F1 - Show this help",
            "  F2 - Toggle users panel",
            "",
            "Chat Commands:",
            "  /help - Server help",
            "  /list - List users",
            "  /private <user> <msg> - Private message",
            "  /quit - Disconnect",
            "",
            "Press any key to continue..."
        ]
        
        # Create help window with proper sizing
        max_line_length = max(len(line) for line in help_text)
        width = max(max_line_length + 6, 50)  # Minimum width of 50
        height = len(help_text) + 4
        
        screen_height, screen_width = self.stdscr.getmaxyx()
        start_y = max(0, (screen_height - height) // 2)
        start_x = max(0, (screen_width - width) // 2)
        
        # Ensure window fits on screen
        if start_x + width > screen_width:
            width = screen_width - start_x - 2
        if start_y + height > screen_height:
            height = screen_height - start_y - 2
            help_text = help_text[:height - 4]  # Truncate if needed
        
        help_win = curses.newwin(height, width, start_y, start_x)
        help_win.box()
        help_win.bkgd(' ', self.color_pairs.get('input_box', curses.A_NORMAL))
        
        for i, line in enumerate(help_text):
            if i < height - 4:  # Leave room for box and padding
                display_line = line[:width - 4] if len(line) > width - 4 else line
                try:
                    help_win.addstr(i + 2, 2, display_line, 
                                  self.color_pairs.get('default', curses.A_NORMAL))
                except curses.error:
                    pass  # Skip if can't fit
        
        help_win.refresh()
        help_win.getch()  # Wait for key press
        help_win.clear()
        help_win.refresh()
        del help_win

    def parse_message(self, message_str: str) -> Optional[Dict[str, Any]]:
        """Parse JSON message from server"""
        try:
            return json.loads(message_str)
        except json.JSONDecodeError:
            return {
                "type": "chat",
                "sender": "unknown",
                "content": message_str,
                "timestamp": datetime.now().isoformat()
            }

    def connect_to_server(self) -> bool:
        """Connect to the chat server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(Config.CONNECTION_TIMEOUT)
            self.socket.connect((Config.SERVER_HOST, Config.SERVER_PORT))
            
            # Wait for nickname request
            response = self.socket.recv(Config.MESSAGE_SIZE_LIMIT).decode('utf-8')
            if response != "NICK":
                return False
            
            # Send nickname
            self.socket.send(self.nickname.encode('utf-8'))
            
            # Wait for response
            response = self.socket.recv(Config.MESSAGE_SIZE_LIMIT).decode('utf-8')
            message = self.parse_message(response)
            
            if message and message.get("type") == "error":
                return False
            
            self.connected = True
            self.users_online = [self.nickname]  # Start with self
            return True
            
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False

    def send_message(self, message: str):
        """Send message to server"""
        if not self.connected or not self.socket:
            return
        
        try:
            self.socket.send(message.encode('utf-8'))
            
            # Display own message immediately for better UX
            if not message.startswith('/'):
                own_message = {
                    "type": "chat",
                    "sender": self.nickname,
                    "content": message,
                    "timestamp": datetime.now().isoformat()
                }
                self.add_message(own_message)
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            self.connected = False

    def handle_server_messages(self):
        """Handle messages from server"""
        while self.running and self.connected:
            try:
                if not self.socket:
                    break
                
                self.socket.settimeout(1.0)
                message_data = self.socket.recv(Config.MESSAGE_SIZE_LIMIT)
                
                if not message_data:
                    self.connected = False
                    break
                
                message_str = message_data.decode('utf-8')
                message = self.parse_message(message_str)
                
                if message:
                    self.add_message(message)
                
            except socket.timeout:
                continue
            except Exception as e:
                self.logger.error(f"Error receiving message: {e}")
                self.connected = False
                break

    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        self.connected = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

    def get_nickname(self):
        """Get nickname from user using simple input"""
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
        self.setup_colors()
        self.setup_windows()

    def run_ui_loop(self):
        """Main UI loop"""
        while self.running:
            try:
                # Refresh UI
                self.refresh_ui()
                
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
        """Start the TUI chat client"""
        self.stdscr = stdscr
        self.running = True
        
        # Setup curses
        curses.curs_set(1)  # Show cursor
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        
        self.setup_colors()
        
        # Get nickname
        self.get_nickname()
        
        # Show connecting message
        self.add_message({
            "type": "system",
            "sender": "SYSTEM",
            "content": f"Connecting to {Config.SERVER_HOST}:{Config.SERVER_PORT}...",
            "timestamp": datetime.now().isoformat()
        })
        self.refresh_ui()
        
        # Connect to server
        if not self.connect_to_server():
            self.add_message({
                "type": "error",
                "sender": "SYSTEM",
                "content": "Failed to connect to server",
                "timestamp": datetime.now().isoformat()
            })
            self.refresh_ui()
            time.sleep(3)
            return
        
        # Add welcome message
        self.add_message({
            "type": "system",
            "sender": "SYSTEM",
            "content": "Connected! Type /help for commands or start chatting. Press F1 for UI help.",
            "timestamp": datetime.now().isoformat()
        })
        
        # Start server message handler
        self.receive_thread = threading.Thread(target=self.handle_server_messages, daemon=True)
        self.receive_thread.start()
        
        # Run UI loop
        self.run_ui_loop()
        
        # Cleanup
        self.disconnect()

def main():
    """Main entry point"""
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