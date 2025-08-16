"""
Client-side UI components for the TUI chat application.
"""
import curses
import textwrap
import sys
import os
from typing import List, Dict, Any
from datetime import datetime

# Add the parent directory to the path to import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.config import MessageType


class Colors:
    """ANSI color codes for fallback."""
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


class UIComponents:
    """Handles all UI components for the TUI client."""
    
    def __init__(self, client):
        self.client = client
        self.color_pairs = {}
    
    def setup_colors(self, stdscr):
        """Initialize curses color pairs."""
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
    
    def setup_windows(self, stdscr):
        """Setup curses windows layout."""
        height, width = stdscr.getmaxyx()
        
        # Calculate window dimensions
        users_width = 20 if self.client.show_users else 0
        chat_width = width - users_width
        chat_height = height - 3  # Leave space for status and input
        
        # Create windows
        self.client.chat_win = curses.newwin(chat_height, chat_width, 0, 0)
        self.client.status_win = curses.newwin(1, width, chat_height, 0)
        self.client.input_win = curses.newwin(2, width, chat_height + 1, 0)
        
        if self.client.show_users and users_width > 0:
            self.client.users_win = curses.newwin(chat_height, users_width, 0, chat_width)
        
        # Configure windows
        self.client.chat_win.scrollok(True)
        self.client.input_win.box()
        if self.client.users_win:
            self.client.users_win.box()
        
        # Set colors
        self.client.status_win.bkgd(' ', self.color_pairs.get('status_bar', curses.A_REVERSE))
    
    def draw_status_bar(self):
        """Draw the status bar."""
        if not self.client.status_win:
            return
            
        height, width = self.client.status_win.getmaxyx()
        self.client.status_win.clear()
        
        # Connection status
        status = "Connected" if self.client.connected else "Disconnected"
        status_color = self.color_pairs.get('success' if self.client.connected else 'error', curses.A_NORMAL)
        
        # Create status text
        left_text = f" {self.client.nickname} | {status}"
        right_text = f"Users: {len(self.client.users_online)} | Press F1 for help "
        
        # Draw status text
        self.client.status_win.addstr(0, 0, left_text[:width-1], status_color)
        
        # Right-align text
        if len(right_text) < width - len(left_text):
            self.client.status_win.addstr(0, width - len(right_text) - 1, right_text, 
                                 self.color_pairs.get('default', curses.A_NORMAL))
        
        self.client.status_win.refresh()
    
    def draw_users_panel(self):
        """Draw the users panel."""
        if not self.client.users_win or not self.client.show_users:
            return
            
        height, width = self.client.users_win.getmaxyx()
        self.client.users_win.clear()
        self.client.users_win.box()
        
        # Title
        title = "Users Online"
        self.client.users_win.addstr(1, 2, title, self.color_pairs.get('users_panel', curses.A_BOLD))
        self.client.users_win.addstr(2, 2, "─" * (width - 4))
        
        # User list
        for i, user in enumerate(self.client.users_online[:height - 5]):
            color = self.color_pairs.get('own_message' if user == self.client.nickname else 'username', 
                                       curses.A_NORMAL)
            indicator = "● " if user == self.client.nickname else "○ "
            user_text = f"{indicator}{user}"
            
            if len(user_text) > width - 4:
                user_text = user_text[:width - 7] + "..."
            
            self.client.users_win.addstr(3 + i, 2, user_text, color)
        
        # Show count if truncated
        if len(self.client.users_online) > height - 5:
            self.client.users_win.addstr(height - 2, 2, f"...and {len(self.client.users_online) - (height - 5)} more", 
                                self.color_pairs.get('system', curses.A_DIM))
        
        self.client.users_win.refresh()
    
    def draw_chat_messages(self):
        """Draw chat messages."""
        if not self.client.chat_win:
            return
            
        height, width = self.client.chat_win.getmaxyx()
        self.client.chat_win.clear()
        
        # Calculate which messages to show
        visible_messages = self.client.messages[-height + self.client.scroll_offset:] if self.client.messages else []
        
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
                    self.client.chat_win.addstr(line, 0, text[:width-1], color)
                except curses.error:
                    pass  # Ignore errors from writing at screen edges
                line += 1
        
        self.client.chat_win.refresh()
    
    def format_message_for_display(self, msg, width: int) -> List[tuple]:
        """Format a message for display with colors."""
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
            if msg.sender == self.client.nickname:
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
        """Draw the input box."""
        if not self.client.input_win:
            return
            
        height, width = self.client.input_win.getmaxyx()
        self.client.input_win.clear()
        self.client.input_win.box()
        
        # Input prompt
        prompt = f" {self.client.nickname}> "
        self.client.input_win.addstr(1, 1, prompt, self.color_pairs.get('username', curses.A_BOLD))
        
        # Current input text
        input_start = len(prompt) + 1
        available_width = width - input_start - 2
        
        # Handle text scrolling if input is too long
        display_text = self.client.current_input
        cursor_display_pos = self.client.input_cursor_pos
        
        if len(display_text) > available_width:
            if cursor_display_pos > available_width - 5:
                # Scroll text to show cursor
                start_pos = cursor_display_pos - available_width + 5
                display_text = display_text[start_pos:]
                cursor_display_pos = cursor_display_pos - start_pos
        
        self.client.input_win.addstr(1, input_start, display_text[:available_width], 
                            self.color_pairs.get('default', curses.A_NORMAL))
        
        # Position cursor
        cursor_x = input_start + cursor_display_pos
        if cursor_x < width - 1:
            self.client.input_win.move(1, cursor_x)
        
        self.client.input_win.refresh()
    
    def refresh_ui(self):
        """Refresh all UI components."""
        try:
            self.draw_status_bar()
            self.draw_users_panel()
            self.draw_chat_messages()
            self.draw_input_box()
        except curses.error:
            pass  # Ignore curses errors during refresh
    
    def show_help_dialog(self, stdscr):
        """Show help dialog."""
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
            "  /history - Show message history",
            "  /quit - Disconnect",
            "",
            "Press any key to continue..."
        ]
        
        # Create help window with proper sizing
        max_line_length = max(len(line) for line in help_text)
        width = max(max_line_length + 6, 50)  # Minimum width of 50
        height = len(help_text) + 4
        
        screen_height, screen_width = stdscr.getmaxyx()
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