"""
Enhanced TUI Chat Client
"""
import sys
import os

# Add the current directory to the path to import client module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from client import main

if __name__ == "__main__":
    main()