"""MCP server that returns the current date and time in fixed formats."""

import re
from datetime import datetime
from importlib.metadata import version
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

# Format name -> strftime pattern. The example values use 2024-12-10 00:54:01 in JST.
# Existing names and patterns must not change; only add new ones.
FORMATS: dict[str, str] = {
    # Basic date formats
    "date": "%Y-%m-%d",  # 2024-12-10
    "date_slash": "%Y/%m/%d",  # 2024/12/10
    "date_jp": "%Y年%m月%d日",  # 2024年12月10日
    # Basic datetime formats
    "datetime": "%Y-%m-%d %H:%M:%S",  # 2024-12-10 00:54:01
    "datetime_jp": "%Y年%m月%d日 %H時%M分%S秒",  # 2024年12月10日 00時54分01秒
    "datetime_t": "%Y-%m-%dT%H:%M:%S",  # 2024-12-10T00:54:01
    # Compact formats for filenames or IDs
    "compact": "%Y%m%d%H%M%S",  # 20241210005401
    "compact_date": "%Y%m%d",  # 20241210
    "compact_time": "%H%M%S",  # 005401
    # Filename formats
    "filename_md": "%Y%m%d%H%M%S.md",  # 20241210005401.md
    "filename_txt": "%Y%m%d%H%M%S.txt",  # 20241210005401.txt
    "filename_log": "%Y%m%d%H%M%S.log",  # 20241210005401.log
    # ISO 8601 formats
    "iso": "%Y-%m-%dT%H:%M:%S%z",  # 2024-12-10T00:54:01+0900
    "iso_basic": "%Y%m%dT%H%M%S%z",  # 20241210T005401+0900
    # Log formats
    "log": "%Y-%m-%d %H:%M:%S.%f",  # 2024-12-10 00:54:01.123456
    "log_compact": "%Y%m%d_%H%M%S",  # 20241210_005401
    # Time-only formats
    "time": "%H:%M:%S",  # 00:54:01
    "time_jp": "%H時%M分%S秒",  # 00時54分01秒
}

_DIRECTIVE = re.compile(r"%.")


def _strftime(dt: datetime, pattern: str) -> str:
    """strftime that keeps non-ASCII text such as "年" out of strftime itself.

    On Windows, Python before 3.12 raises UnicodeEncodeError when the pattern contains
    characters the locale cannot encode, so only the directives are passed to strftime.
    """
    return _DIRECTIVE.sub(lambda m: dt.strftime(m.group()), pattern)


_EXAMPLE = datetime.fromisoformat("2024-12-10T00:54:01.123456+09:00")

GET_DATETIME_DESCRIPTION = (
    "Get the current date and time (local timezone of the machine running the server) "
    "in the given format.\n\nAvailable formats:\n"
    + "\n".join(f"- {name}: {_strftime(_EXAMPLE, pattern)}" for name, pattern in FORMATS.items())
)

mcp = MCPServer("mcp-datetime", version=version("mcp-datetime"))


def format_datetime(format_type: str, now: datetime | None = None) -> str:
    """Return ``now`` (default: the current local time) formatted as ``format_type``."""
    pattern = FORMATS.get(format_type)
    if pattern is None:
        # Use repr so control characters in the input cannot break the message into lines.
        raise ValueError(
            f"Unknown format type: {format_type!r}. Available formats: {', '.join(FORMATS)}"
        )
    if now is None:
        now = datetime.now().astimezone()
    return _strftime(now, pattern)


@mcp.tool(name="get_datetime", description=GET_DATETIME_DESCRIPTION)
def get_datetime(
    format: Annotated[  # noqa: A002 - "format" is the public argument name
        str, Field(description="Format name, e.g. 'datetime'. See the tool description.")
    ],
) -> str:
    """Get the current date and time in the given format."""
    try:
        return format_datetime(format)
    except ValueError as e:
        # ToolError sends the message to the client as an is_error result.
        raise ToolError(str(e)) from e


def main() -> None:
    """Run the server over stdio."""
    mcp.run()
