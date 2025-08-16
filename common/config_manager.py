"""
Configuration management for the chat application.
"""
import json
import os
from typing import Any, Dict
from .config import Config as DefaultConfig


class ConfigManager:
    """Manages application configuration with support for loading from files."""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file
        self.config = {}
        self.load_defaults()
        if config_file and os.path.exists(config_file):
            self.load_from_file()
    
    def load_defaults(self):
        """Load default configuration values."""
        # Copy all attributes from DefaultConfig
        for attr in dir(DefaultConfig):
            if not attr.startswith('_'):
                self.config[attr] = getattr(DefaultConfig, attr)
    
    def load_from_file(self):
        """Load configuration from a JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                file_config = json.load(f)
                self.config.update(file_config)
        except Exception as e:
            print(f"Warning: Could not load config file {self.config_file}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a configuration value."""
        self.config[key] = value
    
    def save_to_file(self):
        """Save configuration to a JSON file."""
        if not self.config_file:
            raise ValueError("No config file specified")
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config file {self.config_file}: {e}")
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values."""
        return self.config.copy()