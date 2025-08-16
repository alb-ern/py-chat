# Enhanced TUI Chat Server

This is an enhanced version of a TUI (Text User Interface) chat server with a modular architecture and the following features:

## Features

1. **Simple Connection**: No authentication required - just enter a nickname to join
2. **Real-time Messaging**: Send and receive messages instantly
3. **Private Messaging**: Send private messages to specific users
4. **Dynamic User List**: Real-time updates of online users
5. **Message History**: View recent chat history on login
6. **Admin Controls**: Kick users and broadcast messages
7. **Modular Architecture**: Clean separation of concerns for easy maintenance
8. **Enhanced Error Handling**: Robust error management and recovery
9. **Protocol Layer**: Dedicated protocol for message formatting
10. **Configuration Management**: Flexible configuration handling

## Server Commands

- `help` - Show available commands
- `list` - List connected clients
- `kick <nickname>` - Kick a user from server
- `broadcast <message>` - Send server announcement
- `stats` - Show server statistics
- `status` - Show current status
- `clear` - Clear console
- `stop` - Shutdown server

## Client Commands

- `/help` - Show help
- `/list` - List online users
- `/private <user> <message>` - Send private message
- `/time` - Show server uptime
- `/history` - Show message history
- `/stats` - Show connection info
- `/quit` - Disconnect

## Modular Structure

The application is organized into the following modules:

### Common Modules
- `common/config.py` - Shared configuration settings
- `common/config_manager.py` - Configuration management
- `common/message.py` - Message handling utilities
- `common/protocol.py` - Protocol definitions
- `common/exceptions.py` - Custom exceptions
- `common/utils.py` - Utility functions

### Client Modules
- `client/__init__.py` - Main client class
- `client/ui.py` - UI components
- `client/network.py` - Network communication

### Server Modules
- `server/__init__.py` - Main server class
- `server/database.py` - Database management
- `server/client_manager.py` - Client management
- `server/network.py` - Network communication
- `server/stats.py` - Statistics tracking

## Usage

1. Start the server: `python tui_server.py`
2. Start clients: `python tui_client.py`
3. Enter your nickname when prompted

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a pull request