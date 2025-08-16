# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-08-16

### Added
- Initial release of the enhanced TUI chat server
- Modular architecture with separate client and server components
- Real-time messaging with private message support
- Dynamic user list with automatic synchronization
- Message history persistence using SQLite
- Admin controls for kicking users and broadcasting messages
- Enhanced TUI with color support and split panels
- Rate limiting to prevent message spam
- Comprehensive error handling and recovery mechanisms
- Configuration management system
- Periodic user list updates to ensure consistency
- Message encryption for secure communication (planned)

### Fixed
- User list display issues for new clients
- USER_LIST messages appearing in chat window
- Message history retrieval for new clients
- Client disconnection handling
- Nickname validation conflicts

### Changed
- Refactored monolithic code into modular structure
- Improved network communication reliability
- Optimized message broadcasting performance
- Enhanced database connection management
- Updated README with comprehensive documentation

### Security
- Implemented input validation and sanitization
- Prevented SQL injection in database queries
- Added message encryption framework (planned for next release)