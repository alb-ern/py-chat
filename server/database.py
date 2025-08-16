"""
Server-side database management for the chat application.
"""
import sqlite3
import hashlib
import secrets
import logging
import sys
import os
from typing import Optional, Tuple, List, Dict

# Add the parent directory to the path to import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.config import MessageType
from common.exceptions import ChatApplicationError


class DatabaseError(ChatApplicationError):
    """Raised when there is a database error."""
    pass


class DatabaseManager:
    """Handles all database operations for the server."""
    
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.db_conn = None
        self.db_cursor = None
        self.setup_database()
    
    def setup_database(self):
        """Setup SQLite database."""
        try:
            self.db_conn = sqlite3.connect(self.db_file, check_same_thread=False)
            self.db_cursor = self.db_conn.cursor()
            
            # Create messages table
            self.db_cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.db_conn.commit()
        except sqlite3.Error as e:
            logging.error(f"SQLite error during database setup: {e}")
            raise DatabaseError(f"Failed to setup database: {e}")
        except Exception as e:
            logging.error(f"Database setup error: {e}")
            raise DatabaseError(f"Failed to setup database: {e}")
    
    def authenticate_user(self, username: str, password: str) -> Optional[Tuple[int, bool]]:
        """Authenticate user with credentials."""
        try:
            self.db_cursor.execute(
                "SELECT id, password_hash, salt, is_admin FROM users WHERE username = ?",
                (username,)
            )
            result = self.db_cursor.fetchone()
            
            if result and self.verify_password(password, result[1], result[2]):
                return (result[0], result[3])  # user_id, is_admin
            return None
        except sqlite3.Error as e:
            logging.error(f"SQLite error during authentication: {e}")
            raise DatabaseError(f"Authentication failed: {e}")
        except Exception as e:
            logging.error(f"Authentication error: {e}")
            raise DatabaseError(f"Authentication failed: {e}")
    
    def register_user(self, username: str, code: str) -> bool:
        """Register a new user with a registration code."""
        try:
            # Check if registration code exists
            self.db_cursor.execute(
                "SELECT id FROM registrations WHERE username = ? AND registration_code = ?",
                (username, code)
            )
            result = self.db_cursor.fetchone()
            
            if not result:
                return False
            
            # Check if user already exists
            self.db_cursor.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,)
            )
            if self.db_cursor.fetchone():
                return False
            
            # Create new user with the registration code as default password
            salt = secrets.token_hex(16)
            password_hash = hashlib.sha256(f"{code}{salt}".encode()).hexdigest()
            
            self.db_cursor.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                (username, password_hash, salt)
            )
            self.db_conn.commit()
            
            # Remove registration code
            self.db_cursor.execute(
                "DELETE FROM registrations WHERE username = ? AND registration_code = ?",
                (username, code)
            )
            self.db_conn.commit()
            
            return True
        except sqlite3.Error as e:
            logging.error(f"SQLite error during registration: {e}")
            raise DatabaseError(f"Registration failed: {e}")
        except Exception as e:
            logging.error(f"Registration error: {e}")
            raise DatabaseError(f"Registration failed: {e}")
    
    def create_registration(self, username: str, code: str) -> bool:
        """Create a new registration code for a user."""
        try:
            # Check if username already exists in registrations
            self.db_cursor.execute(
                "SELECT id FROM registrations WHERE username = ?",
                (username,)
            )
            if self.db_cursor.fetchone():
                return False
            
            # Check if username already exists in users
            self.db_cursor.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,)
            )
            if self.db_cursor.fetchone():
                return False
            
            # Create registration
            self.db_cursor.execute(
                "INSERT INTO registrations (username, registration_code) VALUES (?, ?)",
                (username, code)
            )
            self.db_conn.commit()
            
            return True
        except sqlite3.Error as e:
            logging.error(f"SQLite error creating registration: {e}")
            raise DatabaseError(f"Failed to create registration: {e}")
        except Exception as e:
            logging.error(f"Registration creation error: {e}")
            raise DatabaseError(f"Failed to create registration: {e}")
    
    def save_message(self, msg_type: str, content: str, limit: int = 100):
        """Save message to database."""
        try:
            self.db_cursor.execute(
                "INSERT INTO messages (message_type, content) VALUES (?, ?)",
                (msg_type, content)
            )
            self.db_conn.commit()
            
            # Keep only last N messages
            self.db_cursor.execute("""
                DELETE FROM messages 
                WHERE id NOT IN (
                    SELECT id FROM messages 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                )
            """, (limit,))
            self.db_conn.commit()
        except sqlite3.Error as e:
            logging.error(f"SQLite error saving message: {e}")
            raise DatabaseError(f"Failed to save message: {e}")
        except Exception as e:
            logging.error(f"Error saving message: {e}")
            raise DatabaseError(f"Failed to save message: {e}")
    
    def get_message_history(self, limit: int = 50) -> List[Dict]:
        """Get recent message history."""
        try:
            self.db_cursor.execute("""
                SELECT message_type, content, timestamp
                FROM messages
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            messages = []
            for row in self.db_cursor.fetchall()[::-1]:  # Reverse to get chronological order
                msg_type, content, timestamp = row
                messages.append({
                    "type": msg_type,
                    "content": content,
                    "timestamp": timestamp,
                    "sender": "SYSTEM"  # Default sender for historical messages
                })
            
            return messages
        except sqlite3.Error as e:
            logging.error(f"SQLite error retrieving message history: {e}")
            raise DatabaseError(f"Failed to retrieve message history: {e}")
        except Exception as e:
            logging.error(f"Error retrieving message history: {e}")
            raise DatabaseError(f"Failed to retrieve message history: {e}")
    
    def get_registered_users(self) -> List[Tuple]:
        """Get all registered users."""
        return []
    
    def close(self):
        """Close database connection."""
        if self.db_conn:
            try:
                self.db_conn.close()
            except sqlite3.Error as e:
                logging.error(f"SQLite error closing database: {e}")
            except Exception as e:
                logging.error(f"Error closing database: {e}")