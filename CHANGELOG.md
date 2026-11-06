# Changelog

## [0.1.5] - 2026-11-07
### Fixed
- Pinned the `mcp` dependency to `<2`. mcp 2.x removed the low-level `Server.list_tools` decorator, so 0.1.4 failed to start when installed with uvx.

## [0.1.4] - 2024-12-13
### Changed
- Updated documentation to clarify macOS-only testing status
- Removed Windows-specific references from documentation
- Added prerequisites section in README
- Improved clarity of manual installation examples in documentation
- Restructured README to focus on macOS environment

## [0.1.3] - 2024-12-13
- The fix for 0.1.2 did not work, so we are reverting back to the same content as 0.1.1.

## [0.1.2] - 2024-12-13
### Changed
- Modified entry point in pyproject.toml from `mcp_datetime:main` to `mcp_datetime.server:main` for proper async function execution with uvx
- Improved MCP server compatibility with uvx runtime environment
### Fixed
- Resolved issue where MCP server couldn't be initialized properly when running with simplified uvx configuration

## [0.1.1] - 2024-12-12
### Added
- Initial release to PyPI
- Date and time formatting functionality
- Support for various datetime formats including:
  - Basic date formats (YYYY-MM-DD, YYYY/MM/DD)
  - Japanese date formats (年月日)
  - Basic datetime formats
  - Compact formats for filenames and IDs
  - ISO 8601 formats
  - Log formats
  - Time-only formats
