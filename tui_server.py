"""
Enhanced TUI Chat Server
"""
import sys
import os

# Add the current directory to the path to import server module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import main

if __name__ == "__main__":
    main()