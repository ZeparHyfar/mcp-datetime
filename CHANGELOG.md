# Changelog

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