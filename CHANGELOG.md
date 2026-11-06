# Changelog

## [0.2.0] - 2026-11-07
### Changed
- Rewrote the server with `MCPServer` (the successor of FastMCP) from mcp 2.x. Requires `mcp>=2.3,<3`.
- Supported Python versions are now 3.10 to 3.14 (was 3.12 or later).
- The tool name `get_datetime`, its `format` argument and the existing 18 formats are unchanged.
- An unknown format now returns an error that lists the available formats.

### Added
- Tests and a GitHub Actions workflow.

### Fixed
- An unknown `format` value containing CR/LF could add forged lines to the server log (#8). The value is now quoted with `repr` and is no longer logged by this package.

### Removed
- The stray top-level `__init__.py`.

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
