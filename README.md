# mcp-datetime

[![PyPI](https://img.shields.io/pypi/v/mcp-datetime.svg)](https://pypi.org/project/mcp-datetime/)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/downloads/)
[![MCP SDK](https://img.shields.io/badge/mcp-2.x-green.svg)](https://github.com/modelcontextprotocol/python-sdk)
[![test](https://github.com/ZeparHyfar/mcp-datetime/actions/workflows/test.yml/badge.svg)](https://github.com/ZeparHyfar/mcp-datetime/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

English | [日本語](README_ja.md)

A datetime formatting service implemented as an MCP server for the Claude Desktop Application. Supports generation of datetime strings in various formats.

> **Note**: Day-to-day use is on macOS. Automated tests also run on Linux and Windows.

## Prerequisites

Before using mcp-datetime, ensure you have the following tools installed:

- [uv](https://docs.astral.sh/uv/) (provides `uvx`). uvx downloads a suitable Python (3.10 or later) if needed.

## Features

- ✨ Support for various datetime formats
- 🇯🇵 Japanese language support, including Japanese era (wareki) and weekday
- 🧩 Custom format patterns that work the same on macOS, Linux and Windows
- 📁 Optimized formats for filename generation
- 🌏 Any IANA timezone (`Asia/Tokyo`, `UTC`, `America/New_York`, ...)
- 🔧 Seamless integration with Claude Desktop App

## MCP Server Components

### Tools

The server implements one tool:

- `get_datetime`: Get current date and time in various formats
  - `format` (required): a format name (see [Supported Formats](#supported-formats)) or a custom pattern containing `%` (see [Custom Patterns](#custom-patterns))
  - `timezone` (optional): an IANA timezone name such as `Asia/Tokyo`, `UTC` or `America/New_York`. When omitted, the local timezone of the machine is used
  - Returns formatted datetime string based on specified format

## Usage with Claude Code

```bash
claude mcp add mcp-datetime -- uvx mcp-datetime
```

## Usage with Claude Desktop App

Add the following to your config file:

Config file location (macOS):
`~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mcp-datetime": {
      "command": "uvx",
      "args": ["mcp-datetime"]
    }
  }
}
```

## Updating to the Latest Version

uvx reuses the version it has already cached, so it may keep starting an older version after a new release. To switch to the latest version, clear the cache once and then restart Claude Code or Claude Desktop:

```bash
uv cache clean mcp-datetime
```

The next start downloads the latest version. To always check for the latest version at every start, use `mcp-datetime@latest` instead of `mcp-datetime` in the commands and config above.

## About Installation

If you need to install the package directly (e.g., for development or source code inspection), you can use one of these methods:

- Install from PyPI

  ```bash
  pip install mcp-datetime
  ```

- Install from GitHub Source

  ```bash
  git clone https://github.com/ZeparHyfar/mcp-datetime.git
  cd mcp-datetime
  pip install -e .
  ```

- Example `claude_desktop_config.json` for manual installation

  ```json
  {
    "mcpServers": {
      "mcp-datetime": {
        "command": "/path/to/your/python",
        "args": ["-m", "mcp_datetime"]
      }
    }
  }
  ```

  Replace "/path/to/your/python" with the Python interpreter where you installed the package
  > e.g., "/usr/local/bin/python3" or "/Users/username/.pyenv/versions/3.13.0/bin/python3"

- Run the tests

  ```bash
  uv run --group dev pytest
  ```

## Basic Examples

- Command format

  ```
  # Standard datetime format
  call datetime-service.get_datetime {"format": "datetime"}
  # Result: 2024-12-10 00:54:01

  # Japanese format
  call datetime-service.get_datetime {"format": "datetime_jp"}
  # Result: 2024年12月10日 00時54分01秒

  # Filename format
  call datetime-service.get_datetime {"format": "filename_md"}
  # Result: 20241210005401.md

  # Japanese era (wareki)
  call datetime-service.get_datetime {"format": "date_wareki"}
  # Result: 令和6年12月10日

  # Another timezone
  call datetime-service.get_datetime {"format": "datetime", "timezone": "America/New_York"}
  # Result: 2024-12-09 10:54:01

  # Custom pattern
  call datetime-service.get_datetime {"format": "%Y/%-m/%-d (%a)"}
  # Result: 2024/12/10 (Tue)
  ```

- Claude Desktop App prompt examples

  - User

    ```
    Please tell me the current time in date_slash format
    ```

  - Claude

    ```
    I'll get the current date in date_slash format.

    The current date is 2024/12/12
    ```

## Supported Formats

| Format Name  | Example                     | Description                  |
| ------------ | --------------------------- | ---------------------------- |
| date         | 2024-12-10                  | Standard date format         |
| date_slash   | 2024/12/10                  | Date with slashes            |
| date_jp      | 2024年12月10日              | Japanese date format         |
| datetime     | 2024-12-10 00:54:01         | Standard datetime            |
| datetime_jp  | 2024年12月10日 00時54分01秒 | Japanese datetime            |
| datetime_t   | 2024-12-10T00:54:01         | DateTime with T separator    |
| compact      | 20241210005401              | Compact format for IDs       |
| compact_date | 20241210                    | Compact date only            |
| compact_time | 005401                      | Compact time only            |
| filename_md  | 20241210005401.md           | Markdown filename            |
| filename_txt | 20241210005401.txt          | Text filename                |
| filename_log | 20241210005401.log          | Log filename                 |
| iso          | 2024-12-10T00:54:01+0900    | ISO 8601 format              |
| iso_basic    | 20241210T005401+0900        | Basic ISO format             |
| log          | 2024-12-10 00:54:01.123456  | Log format with microseconds |
| log_compact  | 20241210_005401             | Compact log format           |
| time         | 00:54:01                    | Time only                    |
| time_jp      | 00時54分01秒                | Japanese time format         |
| date_wareki         | 令和6年12月10日                 | Japanese era date                  |
| datetime_wareki     | 令和6年12月10日 00時54分01秒    | Japanese era datetime              |
| date_wareki_short   | R6.12.10                        | Japanese era date, short           |
| date_jp_weekday     | 2024年12月10日（火）            | Japanese date with weekday         |
| datetime_jp_weekday | 2024年12月10日（火） 00時54分01秒 | Japanese datetime with weekday   |
| weekday_jp          | 火曜日                          | Japanese weekday                   |

Japanese era (wareki) is supported from 1873-01-01, when Japan adopted the Gregorian calendar. The first year of an era is written as 元年 (e.g. 令和元年5月1日), except in `date_wareki_short` (R1.5.1).

## Custom Patterns

If `format` contains `%`, it is used as a pattern (up to 200 characters).

- Standard [strftime directives](https://docs.python.org/3/library/datetime.html#format-codes): `%Y %m %d %H %I %M %S %f %p %a %A %b %B %j %U %W %G %V %u %w %z %Z %c %x %X %%`
- No leading zero (works on Windows too): `%-m %-d %-H %-I %-M %-S %-j %-y`
- Japanese directives:

| Directive | Meaning                      | Example (2019-05-01) |
| --------- | ---------------------------- | -------------------- |
| `%Je`     | Era name                     | 令和                 |
| `%JE`     | Era initial                  | R                    |
| `%Jy`     | Era year (元 for year 1)     | 元                   |
| `%JY`     | Era year (always a number)   | 1                    |
| `%Ja`     | Weekday                      | 水                   |
| `%JA`     | Weekday                      | 水曜日               |

Example: `%Je%Jy年%-m月%-d日（%Ja）` → 令和元年5月1日（水）

## Debugging

Since MCP servers run over stdio, debugging can be challenging. We recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

- Using PyPI package

  ```
  npx @modelcontextprotocol/inspector uvx mcp-datetime
  ```

- Using downloaded source code from GitHub

  ```
  git clone https://github.com/ZeparHyfar/mcp-datetime.git
  npx @modelcontextprotocol/inspector uv --directory ./mcp-datetime run mcp-datetime
  ```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
