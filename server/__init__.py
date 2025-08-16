"""
Enhanced Multi-User Chat Server with modular architecture.
"""
import threading
import logging
import json
import time
import sys
import os
import socket
from datetime import datetime
from typing import List, Dict, Optional

# Add the parent directory to the path to import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import Config, MessageType
from common.message import ChatMessage
from server.database import DatabaseManager
from server.client_manager import ClientManager, Client
from server.network import NetworkManager
from server.stats import ServerStats


class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    
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
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'


def colored_print(text: str, color: str = Colors.WHITE, style: str = "", end: str = "\n"):
    """Print colored text."""
    print(f"{style}{color}{text}{Colors.RESET}", end=end)


def print_banner():
    """Print server banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ██████╗██╗  ██╗ █████╗ ████████╗    ███████╗███████╗██████╗║
║  ██╔════╝██║  ██║██╔══██╗╚══██╔══╝    ██╔════╝██╔════╝██╔══██║
║  ██║     ███████║███████║   ██║       ███████╗█████╗  ██████╔╝║
║  ██║     ██╔══██║██╔══██║   ██║       ╚════██║██╔══╝  ██╔══██╗║
║  ╚██████╗██║  ██║██║  ██║   ██║       ███████║███████╗██║  ██║║
║   ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝       ╚══════╝╚══════╝╚═╝  ╚═╝║
║                                                              ║
║              Enhanced Multi-User Chat Server                 ║
║                     with TUI Interface                       ║
╚══════════════════════════════════════════════════════════════╝
    """
    colored_print(banner, Colors.CYAN, Colors.BOLD)


class EnhancedChatServer:
    """Main server class for the enhanced chat application."""
    
    def __init__(self):
        self.client_manager = ClientManager()
        self.db_manager = DatabaseManager(Config.DATABASE_FILE)
        self.network_manager = NetworkManager(self)
        self.stats = ServerStats()
        self.running = False
        
        # UI state
        self.console_history: List[str] = []
        self.max_history = 1000
        
        # Setup logging with colors
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
    
    def setup_logging(self):
        """Setup colored logging."""
        class ColoredFormatter(logging.Formatter):
            COLORS = {
                'DEBUG': Colors.BRIGHT_BLACK,
                'INFO': Colors.CYAN,
                'WARNING': Colors.YELLOW,
                'ERROR': Colors.RED,
                'CRITICAL': Colors.BRIGHT_RED + Colors.BOLD
            }
            
            def format(self, record):
                log_color = self.COLORS.get(record.levelname, Colors.WHITE)
                record.levelname = f"{log_color}{record.levelname}{Colors.RESET}"
                return super().format(record)
        
        # Console handler with colors
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        
        # File handler without colors
        file_handler = logging.FileHandler('chat_server.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        
        logging.basicConfig(
            level=logging.INFO,
            handlers=[console_handler, file_handler]
        )
    
    def log_message(self, message: str, color: str = Colors.WHITE, prefix: str = ""):
        """Add message to console history and optionally print."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {prefix}{message}"
        
        self.console_history.append(formatted_message)
        if len(self.console_history) > self.max_history:
            self.console_history = self.console_history[-500:]
        
        colored_print(formatted_message, color)
    
    def send_user_list(self):
        """Send updated user list to all clients."""
        users = list(self.client_manager.get_nicknames())
        user_list_msg = ChatMessage.create(MessageType.USER_LIST, json.dumps(users))
        self.network_manager.broadcast(user_list_msg)
    
    def remove_client(self, client_fd: int):
        """Remove a client from the server."""
        client = self.client_manager.remove_client(client_fd)
        if not client:
            return
            
        try:
            client.socket.close()
        except:
            pass
        
        # Notify other clients
        leave_msg = ChatMessage.create(MessageType.LEAVE, f"{client.nickname} left the chat")
        self.network_manager.broadcast(leave_msg)
        
        # Send updated user list
        self.send_user_list()
        
        # Log with colors
        uptime = datetime.now() - client.join_time
        self.log_message(
            f"Client disconnected: {client.nickname} ({client.address}) - Session: {uptime}",
            Colors.BRIGHT_RED, "← "
        )
    
    def is_nickname_valid(self, nickname: str) -> tuple[bool, str]:
        """Check if nickname is valid and available."""
        if not nickname or len(nickname.strip()) == 0:
            return False, "Nickname cannot be empty"
        
        nickname = nickname.strip()
        if len(nickname) > 20:
            return False, "Nickname too long (max 20 characters)"
        
        if not nickname.replace('_', '').replace('-', '').isalnum():
            return False, "Nickname can only contain letters, numbers, hyphens, and underscores"
        
        if nickname.lower() in [n.lower() for n in self.client_manager.get_nicknames()]:
            return False, "Nickname already taken"
        
        return True, nickname
    
    def check_rate_limit(self, client: Client) -> bool:
        """Check if client is within rate limits."""
        current_time = time.time()
        
        if current_time - client.last_message_time > Config.RATE_LIMIT_WINDOW:
            client.reset_rate_limit()
        
        if client.message_count >= Config.RATE_LIMIT_MESSAGES:
            return False
        
        client.message_count += 1
        return True
    
    def handle_private_message(self, sender_client: Client, target_nickname: str, content: str):
        """Handle private message between users."""
        target_client = self.client_manager.get_client_by_nickname(target_nickname)
        
        if not target_client:
            error_msg = ChatMessage.create(MessageType.ERROR, f"User '{target_nickname}' not found")
            self.network_manager.send_message(sender_client.socket, error_msg)
            return
        
        # Send private message
        private_msg = ChatMessage.create(MessageType.PRIVATE, content, sender_client.nickname)
        if self.network_manager.send_message(target_client.socket, private_msg):
            # Confirm to sender
            confirm_msg = ChatMessage.create(MessageType.SYSTEM, f"Private message sent to {target_nickname}")
            self.network_manager.send_message(sender_client.socket, confirm_msg)
            
            # Log private message
            self.log_message(
                f"Private message: {sender_client.nickname} → {target_nickname}",
                Colors.MAGENTA, "🔒 "
            )
            self.stats.private_messages += 1
        else:
            self.remove_client(target_client.socket.fileno())
    
    def handle_client_message(self, client_fd: int):
        """Handle messages from a client."""
        client = self.client_manager.get_client_by_fd(client_fd)
        if not client:
            return
            
        while self.running:
            try:
                client.socket.settimeout(1.0)
                message_data = client.socket.recv(Config.MESSAGE_SIZE_LIMIT)
                
                if not message_data:
                    self.remove_client(client_fd)
                    break
                
                message = message_data.decode('utf-8').strip()
                if not message:
                    continue
                
                # Check rate limiting
                if not self.check_rate_limit(client):
                    error_msg = ChatMessage.create(MessageType.ERROR, "Rate limit exceeded. Please slow down.")
                    self.network_manager.send_message(client.socket, error_msg)
                    continue
                
                # Handle special commands
                if message.startswith('/'):
                    self.handle_command(client, message)
                else:
                    # Regular chat message - don't send back to sender
                    chat_msg = ChatMessage.create(MessageType.CHAT, message, client.nickname)
                    self.network_manager.broadcast(chat_msg, exclude_fd=client_fd)
                    
                    # Save message to database
                    self.db_manager.save_message(MessageType.CHAT.value, message)
                    
                    # Log with colors
                    self.log_message(
                        f"[{client.nickname}]: {message}",
                        Colors.GREEN if len(message) < 50 else Colors.YELLOW, "💬 "
                    )
                    
            except socket.timeout:
                continue
            except (ConnectionResetError, ConnectionAbortedError):
                self.remove_client(client_fd)
                break
            except Exception as e:
                self.logger.error(f"Error handling client {client.nickname}: {e}")
                self.remove_client(client_fd)
                break
    
    def handle_command(self, client: Client, command: str):
        """Handle client commands."""
        parts = command[1:].split(' ', 2)
        cmd = parts[0].lower()
        
        self.stats.commands_executed += 1
        
        if cmd == 'help':
            help_text = """Available commands:
/help - Show this help message
/list - List online users  
/private <username> <message> - Send private message
/time - Show server uptime
/history - Show recent message history
/stats - Show your connection info"""
            help_msg = ChatMessage.create(MessageType.SYSTEM, help_text)
            self.network_manager.send_message(client.socket, help_msg)
            
        elif cmd == 'list':
            users = list(self.client_manager.get_nicknames())
            user_list_msg = ChatMessage.create(MessageType.USER_LIST, json.dumps(users))
            self.network_manager.send_message(client.socket, user_list_msg)
            
        elif cmd == 'private' and len(parts) >= 3:
            target_nickname = parts[1]
            message_content = parts[2]
            self.handle_private_message(client, target_nickname, message_content)
            
        elif cmd == 'time':
            uptime = self.stats.get_uptime()
            time_msg = ChatMessage.create(MessageType.SYSTEM, f"Server uptime: {uptime}")
            self.network_manager.send_message(client.socket, time_msg)
            
        elif cmd == 'history':
            # Send message history
            history = self.db_manager.get_message_history()
            if history:
                for msg in history:
                    history_msg = ChatMessage.create(
                        MessageType(msg["type"]), 
                        msg["content"]
                    )
                    self.network_manager.send_message(client.socket, history_msg)
            else:
                no_history_msg = ChatMessage.create(MessageType.SYSTEM, "No message history available")
                self.network_manager.send_message(client.socket, no_history_msg)
                
        elif cmd == 'stats':
            session_time = datetime.now() - client.join_time
            stats_text = f"Your session: {session_time} | Messages sent: {client.message_count}"
            stats_msg = ChatMessage.create(MessageType.SYSTEM, stats_text)
            self.network_manager.send_message(client.socket, stats_msg)
            
        else:
            error_msg = ChatMessage.create(MessageType.ERROR, "Unknown command. Type /help for available commands.")
            self.network_manager.send_message(client.socket, error_msg)
        
        # Log command usage
        self.log_message(
            f"Command executed: /{cmd} by {client.nickname}",
            Colors.CYAN, "⚡ "
        )
    
    def handle_new_client(self, client_socket: socket.socket, address: tuple):
        """Handle new client connection."""
        try:
            # Send nickname request
            if not self.network_manager.send_message(client_socket, "NICK"):
                client_socket.close()
                return
            
            client_socket.settimeout(30.0)
            
            nickname_data = client_socket.recv(Config.MESSAGE_SIZE_LIMIT)
            if not nickname_data:
                client_socket.close()
                return
                
            nickname = nickname_data.decode('utf-8').strip()
            
            # Validate nickname
            is_valid, result = self.is_nickname_valid(nickname)
            if not is_valid:
                error_msg = ChatMessage.create(MessageType.ERROR, result)
                self.network_manager.send_message(client_socket, error_msg)
                client_socket.close()
                return
            
            nickname = result
            
            # Create client object with a default user_id
            client = Client(
                socket=client_socket,
                nickname=nickname,
                address=address,
                join_time=datetime.now(),
                user_id=0  # Default user_id since we're removing authentication
            )
            
            # Add to tracking
            client_fd = client_socket.fileno()
            self.client_manager.add_client(client_fd, client)
            self.stats.total_connections += 1
            
            # Send welcome message and message history
            welcome_msg = ChatMessage.create(MessageType.SYSTEM, f"Welcome to the chat, {nickname}!")
            self.network_manager.send_message(client_socket, welcome_msg)
            
            # Send message history
            history = self.db_manager.get_message_history()
            if history:
                history_msg = ChatMessage.create(MessageType.SYSTEM, "Recent message history:")
                self.network_manager.send_message(client_socket, history_msg)
                
                for msg in history:
                    history_msg = ChatMessage.create(
                        MessageType(msg["type"]), 
                        msg["content"]
                    )
                    self.network_manager.send_message(client_socket, history_msg)
            
            # Notify other clients
            join_msg = ChatMessage.create(MessageType.JOIN, f"{nickname} joined the chat")
            self.network_manager.broadcast(join_msg, exclude_fd=client_fd)
            
            # Log with colors
            self.log_message(
                f"New client connected: {nickname} ({address}) - Total: {self.client_manager.get_client_count()}",
                Colors.BRIGHT_GREEN, "→ "
            )
            
            # Start handling client messages early so they can receive the user list
            client_thread = threading.Thread(
                target=self.handle_client_message, 
                args=(client_fd,),
                name=f"Client-{nickname}",
                daemon=True
            )
            client_thread.start()
            
            # Send updated user list to all clients
            self.send_user_list()
            
        except socket.timeout:
            self.log_message(f"Client {address} timed out during setup", Colors.YELLOW, "⚠ ")
            client_socket.close()
        except Exception as e:
            self.log_message(f"Error handling new client {address}: {e}", Colors.RED, "✗ ")
            client_socket.close()
    
    def print_status_line(self):
        """Print current server status line."""
        uptime = self.stats.get_uptime()
        status_line = (f"├─ Status: {Colors.GREEN}RUNNING{Colors.RESET} │ "
                      f"Uptime: {Colors.CYAN}{uptime}{Colors.RESET} │ "
                      f"Clients: {Colors.YELLOW}{self.client_manager.get_client_count()}/{Config.MAX_CLIENTS}{Colors.RESET} │ "
                      f"Messages: {Colors.MAGENTA}{self.stats.messages_sent}{Colors.RESET}")
        print(f"\r{status_line}", end="", flush=True)
    
    def display_stats(self):
        """Display detailed server statistics."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}╔═══════════════ SERVER STATISTICS ═══════════════╗{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET}                                                  {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Server Uptime:{Colors.RESET}     {Colors.GREEN}{self.stats.get_uptime():>24}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Total Connections:{Colors.RESET}  {Colors.YELLOW}{self.stats.total_connections:>24}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Current Clients:{Colors.RESET}    {Colors.GREEN}{self.client_manager.get_client_count():>24}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Messages Sent:{Colors.RESET}      {Colors.MAGENTA}{self.stats.messages_sent:>24}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Private Messages:{Colors.RESET}   {Colors.BLUE}{self.stats.private_messages:>24}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Commands Executed:{Colors.RESET}  {Colors.CYAN}{self.stats.commands_executed:>24}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Admin Kicks:{Colors.RESET}       {Colors.RED}{self.stats.kicks_issued:>24}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET}                                                  {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}╚══════════════════════════════════════════════════╝{Colors.RESET}\n")
    
    def admin_console(self):
        """Enhanced admin console with colors."""
        colored_print("\n🔧 Admin Console Started", Colors.BRIGHT_GREEN, Colors.BOLD)
        colored_print("Type 'help' for commands, 'stop' to shutdown", Colors.YELLOW)
        
        while self.running:
            try:
                print(f"\n{Colors.BOLD}{Colors.BLUE}admin>{Colors.RESET} ", end="")
                command = input().strip().split()
                
                if not command:
                    continue
                
                cmd = command[0].lower()
                
                if cmd == 'help':
                    help_text = f"""
{Colors.BOLD}{Colors.CYAN}╔══════════════════ ADMIN COMMANDS ══════════════════╗{Colors.RESET}
{Colors.CYAN}║{Colors.RESET}                                                     {Colors.CYAN}║{Colors.RESET}
{Colors.CYAN}║{Colors.RESET} {Colors.GREEN}help{Colors.RESET}                     - Show this help menu       {Colors.CYAN}║{Colors.RESET}
{Colors.CYAN}║{Colors.RESET} {Colors.GREEN}list{Colors.RESET}                     - List all connected clients {Colors.CYAN}║{Colors.RESET}
{Colors.CYAN}║{Colors.RESET} {Colors.GREEN}kick <nickname>{Colors.RESET}          - Kick a user from server   {Colors.CYAN}║{Colors.RESET}
{Colors.CYAN}║{Colors.RESET} {Colors.GREEN}broadcast <message>{Colors.RESET}      - Send server announcement  {Colors.CYAN}║{Colors.RESET}
{Colors.CYAN}║{Colors.RESET} {Colors.GREEN}stats{Colors.RESET}                    - Show detailed statistics  {Colors.CYAN}║{Colors.RESET}
{Colors.CYAN}║{Colors.RESET} {Colors.GREEN}status{Colors.RESET}                   - Show current status line  {Colors.CYAN}║{Colors.RESET}
{Colors.CYAN}║{Colors.RESET} {Colors.GREEN}clear{Colors.RESET}                    - Clear the console screen  {Colors.CYAN}║{Colors.RESET}
{Colors.CYAN}║{Colors.RESET} {Colors.GREEN}stop{Colors.RESET}                     - Shutdown the server safely{Colors.CYAN}║{Colors.RESET}
{Colors.CYAN}║{Colors.RESET}                                                     {Colors.CYAN}║{Colors.RESET}
{Colors.CYAN}╚═════════════════════════════════════════════════════╝{Colors.RESET}"""
                    print(help_text)
                
                elif cmd == 'list':
                    clients = self.client_manager.get_all_clients()
                    if not clients:
                        colored_print("No clients connected", Colors.YELLOW)
                    else:
                        print(f"\n{Colors.BOLD}{Colors.CYAN}Connected Clients ({len(clients)}):{Colors.RESET}")
                        print(f"{Colors.CYAN}{'Nickname':<15} {'Address':<20} {'Connected':<15} {'Messages'}{Colors.RESET}")
                        print(f"{Colors.BRIGHT_BLACK}{'─' * 65}{Colors.RESET}")
                        
                        for client in clients.values():
                            uptime = datetime.now() - client.join_time
                            uptime_str = f"{uptime.seconds//3600:02d}:{(uptime.seconds//60)%60:02d}:{uptime.seconds%60:02d}"
                            
                            print(f"{Colors.GREEN}{client.nickname:<15}{Colors.RESET} "
                                  f"{Colors.BLUE}{str(client.address):<20}{Colors.RESET} "
                                  f"{Colors.YELLOW}{uptime_str:<15}{Colors.RESET} "
                                  f"{Colors.MAGENTA}{client.message_count}{Colors.RESET}")
                
                elif cmd == 'kick' and len(command) > 1:
                    nickname = command[1]
                    client_to_kick = self.client_manager.get_client_by_nickname(nickname)
                    
                    if client_to_kick:
                        kick_msg = ChatMessage.create(MessageType.SYSTEM, "You have been kicked by an administrator")
                        self.network_manager.send_message(client_to_kick.socket, kick_msg)
                        self.remove_client(client_to_kick.socket.fileno())
                        self.stats.kicks_issued += 1
                        colored_print(f"✓ Kicked user: {nickname}", Colors.RED, Colors.BOLD)
                    else:
                        colored_print(f"✗ User '{nickname}' not found", Colors.YELLOW)
                
                elif cmd == 'broadcast' and len(command) > 1:
                    message = ' '.join(command[1:])
                    broadcast_msg = ChatMessage.create(MessageType.SYSTEM, f"📢 ADMIN: {message}")
                    self.network_manager.broadcast(broadcast_msg)
                    colored_print(f"✓ Broadcast sent: {message}", Colors.GREEN, Colors.BOLD)
                
                elif cmd == 'stats':
                    self.display_stats()
                
                elif cmd == 'status':
                    self.print_status_line()
                    print()  # New line after status
                
                elif cmd == 'clear':
                    os.system('clear' if os.name == 'posix' else 'cls')
                    print_banner()
                
                elif cmd == 'users':
                    colored_print("User management is disabled", Colors.YELLOW)
                
                elif cmd == 'stop':
                    colored_print("🛑 Stopping server...", Colors.RED, Colors.BOLD)
                    self.stop_server()
                    break
                
                else:
                    colored_print(f"Unknown command: {cmd}. Type 'help' for available commands.", Colors.YELLOW)
                    
            except KeyboardInterrupt:
                colored_print("\n🛑 Stopping server...", Colors.RED, Colors.BOLD)
                self.stop_server()
                break
            except Exception as e:
                colored_print(f"Error in admin console: {e}", Colors.RED)
    
    def start_server(self):
        """Start the enhanced chat server."""
        try:
            # Clear screen and show banner
            os.system('clear' if os.name == 'posix' else 'cls')
            print_banner()
            
            if not self.network_manager.start_listening(Config.HOST, Config.PORT, Config.MAX_CLIENTS):
                colored_print("❌ Failed to start server", Colors.RED, Colors.BOLD)
                return
            
            self.running = True
            
            colored_print(f"🚀 Chat server started on {Config.HOST}:{Config.PORT}", Colors.BRIGHT_GREEN, Colors.BOLD)
            colored_print(f"📊 Maximum clients: {Config.MAX_CLIENTS}", Colors.CYAN)
            colored_print(f"⚡ Rate limit: {Config.RATE_LIMIT_MESSAGES} messages per {Config.RATE_LIMIT_WINDOW}s", Colors.YELLOW)
            colored_print(f"💾 Database: {Config.DATABASE_FILE}", Colors.CYAN)
            
            # Start admin console
            admin_thread = threading.Thread(target=self.admin_console, name="AdminConsole", daemon=True)
            admin_thread.start()
            
            # Accept connections
            while self.running:
                client_socket, address = self.network_manager.accept_connection()
                if client_socket:
                    if self.client_manager.get_client_count() >= Config.MAX_CLIENTS:
                        error_msg = ChatMessage.create(MessageType.ERROR, "Server is full")
                        self.network_manager.send_message(client_socket, error_msg)
                        client_socket.close()
                        continue
                    
                    connection_thread = threading.Thread(
                        target=self.handle_new_client,
                        args=(client_socket, address),
                        name=f"Connection-{address}",
                        daemon=True
                    )
                    connection_thread.start()
                    
        except Exception as e:
            colored_print(f"❌ Failed to start server: {e}", Colors.RED, Colors.BOLD)
        finally:
            self.stop_server()
    
    def stop_server(self):
        """Stop the server gracefully."""
        self.running = False
        
        # Notify all clients
        shutdown_msg = ChatMessage.create(MessageType.SYSTEM, "🛑 Server is shutting down...")
        self.network_manager.broadcast(shutdown_msg)
        
        # Close all client connections
        for client in list(self.client_manager.get_all_clients().values()):
            try:
                client.socket.close()
            except:
                pass
        
        # Close database connection
        self.db_manager.close()
        
        # Close network manager
        self.network_manager.close()
        
        colored_print(f"✅ Server stopped. Final stats:", Colors.GREEN, Colors.BOLD)
        colored_print(f"   • Total connections: {self.stats.total_connections}", Colors.CYAN)
        colored_print(f"   • Messages sent: {self.stats.messages_sent}", Colors.CYAN)
        colored_print(f"   • Uptime: {self.stats.get_uptime()}", Colors.CYAN)


def main():
    """Main entry point."""
    server = EnhancedChatServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        colored_print("\n🛑 Shutting down...", Colors.RED, Colors.BOLD)
        server.stop_server()
    except Exception as e:
        colored_print(f"❌ Unexpected error: {e}", Colors.RED, Colors.BOLD)


if __name__ == "__main__":
    main()