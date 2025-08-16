#!/usr/bin/env python3
"""
Enhanced TUI Chat Server and Client
"""
import sys
import os

def show_help():
    print("Enhanced TUI Chat Application")
    print("=============================")
    print()
    print("Usage:")
    print("  python main.py server    - Start the chat server")
    print("  python main.py client    - Start a chat client")
    print()
    print("Alternatively, you can run:")
    print("  python tui_server.py     - Start the chat server")
    print("  python tui_client.py     - Start a chat client")
    print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "server":
        # Add the current directory to the path
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from server import main
        main()
    elif command == "client":
        # Add the current directory to the path
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from client import main
        main()
    else:
        show_help()
        sys.exit(1)