# Changelog

## [0.3.0] - Unreleased
### Added
- New tool `convert_time`: convert a time or date-time between timezones, with weekday, UTC offset, time difference and a note for times skipped or repeated by DST.
- New tool `shift_datetime`: add or subtract years, months, weeks, days, hours, minutes and seconds, for the past and the future. Month ends are kept in range.
- New tool `get_datetime_info`: weekday (English and Japanese), Japanese era, ISO week, day of year, quarter, leap year, UTC offset, DST, Unix time, and the difference in days from a reference date (e.g. days until a date).
- Date-time input for the new tools accepts ISO 8601, `2024/12/10`, `2024年12月10日 14時30分`, Japanese era (`令和6年12月10日`, `R6.12.10`) and a time only (`14:30`). Full-width digits are accepted.
- `get_datetime` takes an optional `timezone` argument (IANA name such as `Asia/Tokyo` or `UTC`). Without it, the local timezone is used as before.
- `format` accepts a custom pattern when it contains `%`: strftime directives, `%-m`-style directives without leading zeros that also work on Windows, and Japanese directives `%Je` `%JE` `%Jy` `%JY` `%Ja` `%JA`.
- New formats: `date_wareki`, `datetime_wareki`, `date_wareki_short`, `date_jp_weekday`, `datetime_jp_weekday`, `weekday_jp`. Japanese era is supported from 1873-01-01.
- `tzdata` is installed on Windows, which has no system timezone database.

### Changed
- The existing 18 formats and their output are unchanged.

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
- On Windows with Python 3.10 and 3.11, formats with Japanese text (`date_jp`, `datetime_jp`, `time_jp`) raised `UnicodeEncodeError`. Only the `%` directives are now passed to `strftime`.

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
