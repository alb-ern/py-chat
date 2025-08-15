import threading
import socket
import logging
import json
import time
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

# Color support
class Colors:
    """ANSI color codes for terminal output"""
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
    """Print colored text"""
    print(f"{style}{color}{text}{Colors.RESET}", end=end)

def print_banner():
    """Print server banner"""
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

class Config:
    HOST = '127.0.0.1'
    PORT = 12345
    MAX_CLIENTS = 50
    MESSAGE_SIZE_LIMIT = 1024
    RATE_LIMIT_MESSAGES = 10
    RATE_LIMIT_WINDOW = 60

class MessageType(Enum):
    CHAT = "chat"
    JOIN = "join"
    LEAVE = "leave"
    PRIVATE = "private"
    SYSTEM = "system"
    ERROR = "error"

@dataclass
class Client:
    socket: socket.socket
    nickname: str
    address: tuple
    join_time: datetime
    last_message_time: float = 0
    message_count: int = 0
    
    def reset_rate_limit(self):
        """Reset rate limiting counters"""
        self.message_count = 0
        self.last_message_time = time.time()

class ServerStats:
    def __init__(self):
        self.start_time = datetime.now()
        self.total_connections = 0
        self.messages_sent = 0
        self.private_messages = 0
        self.commands_executed = 0
        self.kicks_issued = 0
    
    def get_uptime(self) -> str:
        uptime = datetime.now() - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

class EnhancedChatServer:
    def __init__(self):
        self.clients: Dict[int, Client] = {}
        self.nicknames: set = set()
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.stats = ServerStats()
        
        # UI state
        self.console_history: List[str] = []
        self.max_history = 1000
        
        # Setup logging with colors
        self.setup_logging()
        self.logger = logging.getLogger(__name__)

    def setup_logging(self):
        """Setup colored logging"""
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
        """Add message to console history and optionally print"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {prefix}{message}"
        
        self.console_history.append(formatted_message)
        if len(self.console_history) > self.max_history:
            self.console_history = self.console_history[-500:]
        
        colored_print(formatted_message, color)

    def create_message(self, msg_type: MessageType, content: str, sender: str = "SERVER") -> str:
        """Create a formatted message"""
        message = {
            "type": msg_type.value,
            "sender": sender,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(message)

    def broadcast(self, message: str, exclude_fd: Optional[int] = None):
        """Send message to all connected clients except excluded one"""
        disconnected = []
        sent_count = 0
        
        for fd, client in self.clients.items():
            if exclude_fd and fd == exclude_fd:
                continue
            try:
                client.socket.send(message.encode('utf-8'))
                sent_count += 1
            except (ConnectionResetError, BrokenPipeError):
                disconnected.append(fd)
            except Exception as e:
                self.logger.error(f"Error broadcasting to {client.nickname}: {e}")
                disconnected.append(fd)
        
        # Remove disconnected clients
        for fd in disconnected:
            self.remove_client(fd)
        
        self.stats.messages_sent += sent_count

    def remove_client(self, client_fd: int):
        """Remove a client from the server"""
        if client_fd not in self.clients:
            return
            
        client = self.clients[client_fd]
        try:
            client.socket.close()
        except:
            pass
        
        # Remove from tracking
        del self.clients[client_fd]
        self.nicknames.discard(client.nickname)
        
        # Notify other clients
        leave_msg = self.create_message(MessageType.LEAVE, f"{client.nickname} left the chat")
        self.broadcast(leave_msg)
        
        # Log with colors
        uptime = datetime.now() - client.join_time
        self.log_message(
            f"Client disconnected: {client.nickname} ({client.address}) - Session: {uptime}",
            Colors.BRIGHT_RED, "← "
        )

    def is_nickname_valid(self, nickname: str) -> tuple[bool, str]:
        """Check if nickname is valid and available"""
        if not nickname or len(nickname.strip()) == 0:
            return False, "Nickname cannot be empty"
        
        nickname = nickname.strip()
        if len(nickname) > 20:
            return False, "Nickname too long (max 20 characters)"
        
        if not nickname.replace('_', '').replace('-', '').isalnum():
            return False, "Nickname can only contain letters, numbers, hyphens, and underscores"
        
        if nickname.lower() in [n.lower() for n in self.nicknames]:
            return False, "Nickname already taken"
        
        return True, nickname

    def check_rate_limit(self, client: Client) -> bool:
        """Check if client is within rate limits"""
        current_time = time.time()
        
        if current_time - client.last_message_time > Config.RATE_LIMIT_WINDOW:
            client.reset_rate_limit()
        
        if client.message_count >= Config.RATE_LIMIT_MESSAGES:
            return False
        
        client.message_count += 1
        return True

    def handle_private_message(self, sender_client: Client, target_nickname: str, content: str):
        """Handle private message between users"""
        target_client = None
        for client in self.clients.values():
            if client.nickname.lower() == target_nickname.lower():
                target_client = client
                break
        
        if not target_client:
            error_msg = self.create_message(MessageType.ERROR, f"User '{target_nickname}' not found")
            sender_client.socket.send(error_msg.encode('utf-8'))
            return
        
        # Send private message
        private_msg = self.create_message(MessageType.PRIVATE, content, sender_client.nickname)
        try:
            target_client.socket.send(private_msg.encode('utf-8'))
            
            # Confirm to sender
            confirm_msg = self.create_message(MessageType.SYSTEM, f"Private message sent to {target_nickname}")
            sender_client.socket.send(confirm_msg.encode('utf-8'))
            
            # Log private message
            self.log_message(
                f"Private message: {sender_client.nickname} → {target_nickname}",
                Colors.MAGENTA, "🔒 "
            )
            self.stats.private_messages += 1
            
        except Exception as e:
            self.logger.error(f"Error sending private message: {e}")

    def handle_client_message(self, client_fd: int):
        """Handle messages from a client"""
        client = self.clients.get(client_fd)
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
                    error_msg = self.create_message(MessageType.ERROR, "Rate limit exceeded. Please slow down.")
                    client.socket.send(error_msg.encode('utf-8'))
                    continue
                
                # Handle special commands
                if message.startswith('/'):
                    self.handle_command(client, message)
                else:
                    # Regular chat message - don't send back to sender
                    chat_msg = self.create_message(MessageType.CHAT, message, client.nickname)
                    self.broadcast(chat_msg, exclude_fd=client_fd)
                    
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
        """Handle client commands"""
        parts = command[1:].split(' ', 2)
        cmd = parts[0].lower()
        
        self.stats.commands_executed += 1
        
        if cmd == 'help':
            help_text = """Available commands:
/help - Show this help message
/list - List online users  
/private <username> <message> - Send private message
/time - Show server uptime
/stats - Show your connection info"""
            help_msg = self.create_message(MessageType.SYSTEM, help_text)
            client.socket.send(help_msg.encode('utf-8'))
            
        elif cmd == 'list':
            users = [c.nickname for c in self.clients.values()]
            user_list = f"Online users ({len(users)}): {', '.join(users)}"
            list_msg = self.create_message(MessageType.SYSTEM, user_list)
            client.socket.send(list_msg.encode('utf-8'))
            
        elif cmd == 'private' and len(parts) >= 3:
            target_nickname = parts[1]
            message_content = parts[2]
            self.handle_private_message(client, target_nickname, message_content)
            
        elif cmd == 'time':
            uptime = self.stats.get_uptime()
            time_msg = self.create_message(MessageType.SYSTEM, f"Server uptime: {uptime}")
            client.socket.send(time_msg.encode('utf-8'))
            
        elif cmd == 'stats':
            session_time = datetime.now() - client.join_time
            stats_text = f"Your session: {session_time} | Messages sent: {client.message_count}"
            stats_msg = self.create_message(MessageType.SYSTEM, stats_text)
            client.socket.send(stats_msg.encode('utf-8'))
            
        else:
            error_msg = self.create_message(MessageType.ERROR, "Unknown command. Type /help for available commands.")
            client.socket.send(error_msg.encode('utf-8'))
        
        # Log command usage
        self.log_message(
            f"Command executed: /{cmd} by {client.nickname}",
            Colors.CYAN, "⚡ "
        )

    def handle_new_client(self, client_socket: socket.socket, address: tuple):
        """Handle new client connection"""
        try:
            client_socket.send("NICK".encode('utf-8'))
            client_socket.settimeout(30.0)
            
            nickname_data = client_socket.recv(Config.MESSAGE_SIZE_LIMIT)
            if not nickname_data:
                client_socket.close()
                return
                
            nickname = nickname_data.decode('utf-8').strip()
            
            # Validate nickname
            is_valid, result = self.is_nickname_valid(nickname)
            if not is_valid:
                error_msg = self.create_message(MessageType.ERROR, result)
                client_socket.send(error_msg.encode('utf-8'))
                client_socket.close()
                return
            
            nickname = result
            
            # Create client object
            client = Client(
                socket=client_socket,
                nickname=nickname,
                address=address,
                join_time=datetime.now()
            )
            
            # Add to tracking
            client_fd = client_socket.fileno()
            self.clients[client_fd] = client
            self.nicknames.add(nickname)
            self.stats.total_connections += 1
            
            # Send welcome message
            welcome_msg = self.create_message(MessageType.SYSTEM, f"Welcome to the chat, {nickname}!")
            client_socket.send(welcome_msg.encode('utf-8'))
            
            # Notify other clients
            join_msg = self.create_message(MessageType.JOIN, f"{nickname} joined the chat")
            self.broadcast(join_msg, exclude_fd=client_fd)
            
            # Log with colors
            self.log_message(
                f"New client connected: {nickname} ({address}) - Total: {len(self.clients)}",
                Colors.BRIGHT_GREEN, "→ "
            )
            
            # Start handling client messages
            client_thread = threading.Thread(
                target=self.handle_client_message, 
                args=(client_fd,),
                name=f"Client-{nickname}",
                daemon=True
            )
            client_thread.start()
            
        except socket.timeout:
            self.log_message(f"Client {address} timed out during setup", Colors.YELLOW, "⚠ ")
            client_socket.close()
        except Exception as e:
            self.log_message(f"Error handling new client {address}: {e}", Colors.RED, "✗ ")
            client_socket.close()

    def print_status_line(self):
        """Print current server status line"""
        uptime = self.stats.get_uptime()
        status_line = (f"├─ Status: {Colors.GREEN}RUNNING{Colors.RESET} │ "
                      f"Uptime: {Colors.CYAN}{uptime}{Colors.RESET} │ "
                      f"Clients: {Colors.YELLOW}{len(self.clients)}/{Config.MAX_CLIENTS}{Colors.RESET} │ "
                      f"Messages: {Colors.MAGENTA}{self.stats.messages_sent}{Colors.RESET}")
        print(f"\r{status_line}", end="", flush=True)

    def display_stats(self):
        """Display detailed server statistics"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}╔═══════════════ SERVER STATISTICS ═══════════════╗{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET}                                                  {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Server Uptime:{Colors.RESET}     {Colors.GREEN}{self.stats.get_uptime():>24}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Total Connections:{Colors.RESET}  {Colors.YELLOW}{self.stats.total_connections:>24}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Current Clients:{Colors.RESET}    {Colors.GREEN}{len(self.clients):>24}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Messages Sent:{Colors.RESET}      {Colors.MAGENTA}{self.stats.messages_sent:>24}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Private Messages:{Colors.RESET}   {Colors.BLUE}{self.stats.private_messages:>24}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Commands Executed:{Colors.RESET}  {Colors.CYAN}{self.stats.commands_executed:>24}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Admin Kicks:{Colors.RESET}       {Colors.RED}{self.stats.kicks_issued:>24}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET}                                                  {Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}╚══════════════════════════════════════════════════╝{Colors.RESET}\n")

    def admin_console(self):
        """Enhanced admin console with colors"""
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
                    if not self.clients:
                        colored_print("No clients connected", Colors.YELLOW)
                    else:
                        print(f"\n{Colors.BOLD}{Colors.CYAN}Connected Clients ({len(self.clients)}):{Colors.RESET}")
                        print(f"{Colors.CYAN}{'Nickname':<15} {'Address':<20} {'Connected':<15} {'Messages'}{Colors.RESET}")
                        print(f"{Colors.BRIGHT_BLACK}{'─' * 65}{Colors.RESET}")
                        
                        for client in self.clients.values():
                            uptime = datetime.now() - client.join_time
                            uptime_str = f"{uptime.seconds//3600:02d}:{(uptime.seconds//60)%60:02d}:{uptime.seconds%60:02d}"
                            
                            print(f"{Colors.GREEN}{client.nickname:<15}{Colors.RESET} "
                                  f"{Colors.BLUE}{str(client.address):<20}{Colors.RESET} "
                                  f"{Colors.YELLOW}{uptime_str:<15}{Colors.RESET} "
                                  f"{Colors.MAGENTA}{client.message_count}{Colors.RESET}")
                
                elif cmd == 'kick' and len(command) > 1:
                    nickname = command[1]
                    client_to_kick = None
                    for client in self.clients.values():
                        if client.nickname.lower() == nickname.lower():
                            client_to_kick = client
                            break
                    
                    if client_to_kick:
                        kick_msg = self.create_message(MessageType.SYSTEM, "You have been kicked by an administrator")
                        client_to_kick.socket.send(kick_msg.encode('utf-8'))
                        self.remove_client(client_to_kick.socket.fileno())
                        self.stats.kicks_issued += 1
                        colored_print(f"✓ Kicked user: {nickname}", Colors.RED, Colors.BOLD)
                    else:
                        colored_print(f"✗ User '{nickname}' not found", Colors.YELLOW)
                
                elif cmd == 'broadcast' and len(command) > 1:
                    message = ' '.join(command[1:])
                    broadcast_msg = self.create_message(MessageType.SYSTEM, f"📢 ADMIN: {message}")
                    self.broadcast(broadcast_msg)
                    colored_print(f"✓ Broadcast sent: {message}", Colors.GREEN, Colors.BOLD)
                
                elif cmd == 'stats':
                    self.display_stats()
                
                elif cmd == 'status':
                    self.print_status_line()
                    print()  # New line after status
                
                elif cmd == 'clear':
                    os.system('clear' if os.name == 'posix' else 'cls')
                    print_banner()
                
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
        """Start the enhanced chat server"""
        try:
            # Clear screen and show banner
            os.system('clear' if os.name == 'posix' else 'cls')
            print_banner()
            
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((Config.HOST, Config.PORT))
            self.server_socket.listen(Config.MAX_CLIENTS)
            self.running = True
            
            colored_print(f"🚀 Chat server started on {Config.HOST}:{Config.PORT}", Colors.BRIGHT_GREEN, Colors.BOLD)
            colored_print(f"📊 Maximum clients: {Config.MAX_CLIENTS}", Colors.CYAN)
            colored_print(f"⚡ Rate limit: {Config.RATE_LIMIT_MESSAGES} messages per {Config.RATE_LIMIT_WINDOW}s", Colors.YELLOW)
            
            # Start admin console
            admin_thread = threading.Thread(target=self.admin_console, name="AdminConsole", daemon=True)
            admin_thread.start()
            
            # Accept connections
            while self.running:
                try:
                    self.server_socket.settimeout(1.0)
                    client_socket, address = self.server_socket.accept()
                    
                    if len(self.clients) >= Config.MAX_CLIENTS:
                        error_msg = self.create_message(MessageType.ERROR, "Server is full")
                        client_socket.send(error_msg.encode('utf-8'))
                        client_socket.close()
                        continue
                    
                    connection_thread = threading.Thread(
                        target=self.handle_new_client,
                        args=(client_socket, address),
                        name=f"Connection-{address}",
                        daemon=True
                    )
                    connection_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Error accepting connection: {e}")
                        
        except Exception as e:
            colored_print(f"❌ Failed to start server: {e}", Colors.RED, Colors.BOLD)
        finally:
            self.stop_server()

    def stop_server(self):
        """Stop the server gracefully"""
        self.running = False
        
        # Notify all clients
        shutdown_msg = self.create_message(MessageType.SYSTEM, "🛑 Server is shutting down...")
        self.broadcast(shutdown_msg)
        
        # Close all client connections
        for client in list(self.clients.values()):
            try:
                client.socket.close()
            except:
                pass
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        colored_print(f"✅ Server stopped. Final stats:", Colors.GREEN, Colors.BOLD)
        colored_print(f"   • Total connections: {self.stats.total_connections}", Colors.CYAN)
        colored_print(f"   • Messages sent: {self.stats.messages_sent}", Colors.CYAN)
        colored_print(f"   • Uptime: {self.stats.get_uptime()}", Colors.CYAN)

def main():
    """Main entry point"""
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