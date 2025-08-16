"""
Server-side statistics tracking for the chat application.
"""
from datetime import datetime


class ServerStats:
    """Tracks server statistics."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.total_connections = 0
        self.messages_sent = 0
        self.private_messages = 0
        self.commands_executed = 0
        self.kicks_issued = 0
    
    def get_uptime(self) -> str:
        """Get server uptime as a formatted string."""
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