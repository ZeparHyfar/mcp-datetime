"""MCP server that returns the current date and time in many formats."""

import re
from datetime import date, datetime
from datetime import tzinfo as TzInfo
from importlib.metadata import version
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

# Format name -> pattern. The example values use 2024-12-10 00:54:01 (Tuesday) in JST.
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
    # Japanese era (wareki) and weekday formats (added in 0.3.0)
    "date_wareki": "%Je%Jy年%-m月%-d日",  # 令和6年12月10日
    "datetime_wareki": "%Je%Jy年%-m月%-d日 %H時%M分%S秒",  # 令和6年12月10日 00時54分01秒
    "date_wareki_short": "%JE%JY.%-m.%-d",  # R6.12.10
    "date_jp_weekday": "%Y年%m月%d日（%Ja）",  # 2024年12月10日（火）
    "datetime_jp_weekday": "%Y年%m月%d日（%Ja） %H時%M分%S秒",  # 2024年12月10日（火） 00時54分01秒
    "weekday_jp": "%JA",  # 火曜日
}

# Japanese eras: (first day in the Gregorian calendar, name, initial, Gregorian year of year 1 minus 1).
# Meiji is supported only from 1873-01-01, when Japan adopted the Gregorian calendar.
WAREKI_START = date(1873, 1, 1)
_ERAS: list[tuple[date, str, str, int]] = [
    (date(2019, 5, 1), "令和", "R", 2018),
    (date(1989, 1, 8), "平成", "H", 1988),
    (date(1926, 12, 25), "昭和", "S", 1925),
    (date(1912, 7, 30), "大正", "T", 1911),
    (WAREKI_START, "明治", "M", 1867),
]

_WEEKDAYS_JP = "月火水木金土日"

# Standard strftime directives that work the same on Linux, macOS and Windows.
_STANDARD = set("aAbBcdfGHIjmMpSuUVwWxXyYzZ%")
# Directives that may take "-" to drop leading zeros, e.g. %-m -> 1 instead of 01.
_NO_PAD = set("dmHIMSjy")

_DIRECTIVE = re.compile(r"%(?:J.|-.|.)", re.DOTALL)
MAX_PATTERN_LENGTH = 200

DEFAULT_FORMAT_HINT = "a format name such as 'datetime', or a pattern containing '%'"


def _era(d: date) -> tuple[str, str, int]:
    """Return (era name, era initial, year in the era) for ``d``."""
    for start, name, initial, offset in _ERAS:
        if d >= start:
            return name, initial, d.year - offset
    raise ValueError(
        f"Japanese era (wareki) is supported from {WAREKI_START.isoformat()}; got {d.isoformat()}."
    )


def _directive(dt: datetime, token: str) -> str:
    """Expand a single directive such as '%Y', '%-m' or '%Je'."""
    code = token[1:]
    if code.startswith("J") and len(code) == 2:
        kind = code[1]
        if kind in "aA":
            weekday = _WEEKDAYS_JP[dt.weekday()]
            return weekday if kind == "a" else weekday + "曜日"
        if kind in "eEyY":
            name, initial, year = _era(dt.date())
            if kind == "e":
                return name
            if kind == "E":
                return initial
            if kind == "y" and year == 1:
                return "元"
            return str(year)
    elif code.startswith("-") and len(code) == 2 and code[1] in _NO_PAD:
        return dt.strftime("%" + code[1]).lstrip("0") or "0"
    elif code in _STANDARD:
        return dt.strftime(token)
    raise ValueError(f"Unknown directive {token!r} in the format.")


def _strftime(dt: datetime, pattern: str) -> str:
    """Format ``dt`` with ``pattern``, supporting %-x (no padding) and %J (Japanese) directives.

    Only single directives are passed to strftime. On Windows, Python before 3.12 raises
    UnicodeEncodeError when the pattern contains characters the locale cannot encode, and
    unknown directives behave differently on each platform.
    """
    return _DIRECTIVE.sub(lambda m: _directive(dt, m.group()), pattern)


def resolve_timezone(name: str | None) -> TzInfo | None:
    """Return the IANA timezone ``name``, or None for the local timezone."""
    if name is None or not name.strip():
        return None
    try:
        return ZoneInfo(name.strip())
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise ValueError(
            f"Unknown timezone: {name!r}. Use an IANA name such as 'Asia/Tokyo', 'UTC' "
            "or 'America/New_York'."
        ) from e


def format_datetime(
    format_type: str, now: datetime | None = None, timezone: str | None = None
) -> str:
    """Return ``now`` (default: the current time) formatted as ``format_type``.

    ``format_type`` is a name in FORMATS, or a pattern if it contains '%'.
    ``timezone`` is an IANA name; None means the local timezone of the machine.
    """
    # Use repr in messages so control characters in the input cannot break them into lines.
    if "%" in format_type:
        if len(format_type) > MAX_PATTERN_LENGTH:
            raise ValueError(f"The format pattern is longer than {MAX_PATTERN_LENGTH} characters.")
        pattern = format_type
    else:
        pattern = FORMATS.get(format_type)
        if pattern is None:
            raise ValueError(
                f"Unknown format type: {format_type!r}. Use {DEFAULT_FORMAT_HINT}. "
                f"Available formats: {', '.join(FORMATS)}"
            )
    tz = resolve_timezone(timezone)
    if now is None:
        now = datetime.now(tz) if tz else datetime.now().astimezone()
    elif tz:
        now = now.astimezone(tz)
    return _strftime(now, pattern)


_EXAMPLE = datetime.fromisoformat("2024-12-10T00:54:01.123456+09:00")

GET_DATETIME_DESCRIPTION = (
    "Get the current date and time in the given format.\n\n"
    "The time is in the local timezone of the machine running the server, "
    "unless 'timezone' is given as an IANA name such as 'Asia/Tokyo' or 'UTC'.\n\n"
    "'format' is one of the format names below, or a custom pattern containing '%'.\n"
    "Custom patterns accept strftime directives (%Y %m %d %H %M %S %a %A %b %B %z %Z %j ...), "
    "%-m %-d %-H %-M %-S %-I %-j %-y for no leading zero, and these Japanese directives: "
    "%Je era name (令和), %JE era initial (R), %Jy era year (元 for year 1), "
    "%JY era year (always a number), %Ja weekday (火), %JA weekday (火曜日). "
    "Example: '%Je%Jy年%-m月%-d日（%Ja）' -> 令和6年12月10日（火）. "
    "Japanese era is supported from 1873-01-01.\n\n"
    "Available formats (example: 2024-12-10 00:54:01 JST):\n"
    + "\n".join(f"- {name}: {_strftime(_EXAMPLE, pattern)}" for name, pattern in FORMATS.items())
)

mcp = MCPServer("mcp-datetime", version=version("mcp-datetime"))


@mcp.tool(name="get_datetime", description=GET_DATETIME_DESCRIPTION)
def get_datetime(
    format: Annotated[  # noqa: A002 - "format" is the public argument name
        str,
        Field(
            description="Format name such as 'datetime', or a custom pattern containing '%'. "
            "See the tool description."
        ),
    ],
    timezone: Annotated[
        str | None,
        Field(
            description="IANA timezone name such as 'Asia/Tokyo', 'UTC' or 'America/New_York'. "
            "Omit to use the local timezone of the machine."
        ),
    ] = None,
) -> str:
    """Get the current date and time in the given format."""
    try:
        return format_datetime(format, timezone=timezone)
    except ValueError as e:
        # ToolError sends the message to the client as an is_error result.
        raise ToolError(str(e)) from e


def main() -> None:
    """Run the server over stdio."""
    mcp.run()
