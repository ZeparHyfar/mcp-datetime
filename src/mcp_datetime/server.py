"""MCP server that returns the current date and time in many formats."""

import calendar
import re
import unicodedata
from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_timezone
from datetime import tzinfo as TzInfo
from importlib.metadata import version
from typing import Annotated, Any
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
_TIMEZONE_NAME = re.compile(r"[A-Za-z0-9_+\-]+(?:/[A-Za-z0-9_+\-]+)*")

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
    message = (
        f"Unknown timezone: {name!r}. Use an IANA name such as 'Asia/Tokyo', 'UTC' "
        "or 'America/New_York'."
    )
    key = name.strip()
    # Check the characters first: on Windows, ZoneInfo raises OSError with the file path
    # for names such as one containing a newline.
    if not _TIMEZONE_NAME.fullmatch(key):
        raise ValueError(message)
    try:
        return ZoneInfo(key)
    except (ZoneInfoNotFoundError, ValueError, OSError) as e:
        raise ValueError(message) from e


def format_datetime(
    format_type: str, now: datetime | None = None, timezone: str | None = None
) -> str:
    """Return ``now`` (default: the current time) formatted as ``format_type``.

    ``format_type`` is a name in FORMATS, or a pattern if it contains '%'.
    ``timezone`` is an IANA name; None means the local timezone of the machine.
    """
    pattern = _pattern(format_type)
    tz = resolve_timezone(timezone)
    if now is None:
        now = _now(tz)
    elif tz:
        now = now.astimezone(tz)
    return _strftime(now, pattern)


def _pattern(format_type: str) -> str:
    """Return the pattern for a format name, or ``format_type`` itself if it contains '%'."""
    # Use repr in messages so control characters in the input cannot break them into lines.
    if "%" in format_type:
        if len(format_type) > MAX_PATTERN_LENGTH:
            raise ValueError(f"The format pattern is longer than {MAX_PATTERN_LENGTH} characters.")
        return format_type
    pattern = FORMATS.get(format_type)
    if pattern is None:
        raise ValueError(
            f"Unknown format type: {format_type!r}. Use {DEFAULT_FORMAT_HINT}. "
            f"Available formats: {', '.join(FORMATS)}"
        )
    return pattern


def _now(tz: TzInfo | None) -> datetime:
    """Return the current time in ``tz``, or in the local timezone if ``tz`` is None."""
    return datetime.now(tz) if tz else datetime.now().astimezone()


# ---------------------------------------------------------------------------
# Parsing date and time input
# ---------------------------------------------------------------------------

MAX_INPUT_LENGTH = 100

_TIME_PART = r"(?P<H>\d{1,2})(?::|時)(?P<M>\d{1,2})(?:(?::|分)(?P<S>\d{1,2})(?:\.(?P<f>\d{1,6}))?秒?|分)?"
_OFFSET_PART = r"(?P<tz>Z|[+-]\d{2}:?\d{2})"
_ISO_INPUT = re.compile(
    r"(?P<y>\d{4})[-/](?P<m>\d{1,2})[-/](?P<d>\d{1,2})"
    rf"(?:(?:T|\s+){_TIME_PART})?\s*{_OFFSET_PART}?",
    re.IGNORECASE,
)
_JP_INPUT = re.compile(
    rf"(?P<y>\d{{4}})年(?P<m>\d{{1,2}})月(?P<d>\d{{1,2}})日(?:\s*{_TIME_PART})?"
)
_WAREKI_INPUT = re.compile(
    r"(?P<era>明治|大正|昭和|平成|令和|[MTSHR])\.?\s*(?P<y>元|\d{1,2})(?:年|[./-])"
    r"(?P<m>\d{1,2})(?:月|[./-])(?P<d>\d{1,2})日?"
    rf"(?:\s*{_TIME_PART})?",
    re.IGNORECASE,
)
_TIME_INPUT = re.compile(rf"{_TIME_PART}\s*{_OFFSET_PART}?", re.IGNORECASE)

_ERA_BY_KEY = {key: era for era in _ERAS for key in (era[1], era[2])}


def _date_of(m: re.Match, text: str) -> date:
    try:
        return date(int(m.group("y")), int(m.group("m")), int(m.group("d")))
    except ValueError as e:
        raise ValueError(f"{text!r} is not a valid date: {e}.") from e


def _time_of(m: re.Match, text: str) -> time:
    if m.group("H") is None:
        return time(0, 0)
    micro = int((m.group("f") or "0").ljust(6, "0"))
    try:
        return time(int(m.group("H")), int(m.group("M")), int(m.group("S") or 0), micro)
    except ValueError as e:
        raise ValueError(f"{text!r} is not a valid time: {e}.") from e


def _offset_of(m: re.Match) -> TzInfo | None:
    value = m.group("tz")
    if not value:
        return None
    if value.upper() == "Z":
        return dt_timezone.utc
    sign = -1 if value[0] == "-" else 1
    digits = value[1:].replace(":", "")
    return dt_timezone(sign * timedelta(hours=int(digits[:2]), minutes=int(digits[2:])))


def _wareki_date(era_key: str, year_text: str, month: int, day: int) -> date:
    """Convert a Japanese era date to a Gregorian date, checking that it really exists."""
    start, name, _initial, offset = _ERA_BY_KEY[era_key.upper() if era_key.isascii() else era_key]
    era_year = 1 if year_text == "元" else int(year_text)
    label = f"{name}{'元' if era_year == 1 else era_year}年{month}月{day}日"
    try:
        result = date(era_year + offset, month, day)
    except ValueError as e:
        raise ValueError(f"{label} is not a valid date.") from e
    if result < WAREKI_START:
        _era(result)  # raises the "supported from 1873-01-01" error
    if era_year < 1 or result < start or _era(result)[0] != name:
        raise ValueError(f"{label} does not exist in the Japanese era calendar.")
    return result


def parse_datetime(text: str, tz: TzInfo | None, now: datetime | None = None) -> datetime:
    """Parse ``text`` into an aware datetime.

    Accepts ISO 8601 style (2024-12-10, 2024-12-10 14:30, 2024-12-10T14:30:00+09:00),
    2024/12/10, 2024年12月10日 14時30分, Japanese era (令和6年12月10日, R6.12.10) and a time
    only (14:30, meaning today). Without an offset in ``text``, the time is in ``tz``
    (None means the local timezone).
    """
    if len(text) > MAX_INPUT_LENGTH:
        raise ValueError(f"The date/time is longer than {MAX_INPUT_LENGTH} characters.")
    # NFKC turns full-width digits and symbols (１２：３０) and ㍻-style era signs into plain text.
    value = unicodedata.normalize("NFKC", text).strip()
    offset: TzInfo | None = None
    if m := _ISO_INPUT.fullmatch(value):
        day, clock, offset = _date_of(m, text), _time_of(m, text), _offset_of(m)
    elif m := _JP_INPUT.fullmatch(value):
        day, clock = _date_of(m, text), _time_of(m, text)
    elif m := _WAREKI_INPUT.fullmatch(value):
        day = _wareki_date(m.group("era"), m.group("y"), int(m.group("m")), int(m.group("d")))
        clock = _time_of(m, text)
    elif m := _TIME_INPUT.fullmatch(value):
        clock, offset = _time_of(m, text), _offset_of(m)
        day = (now or _now(offset or tz)).astimezone(offset or tz).date()
    else:
        raise ValueError(
            f"Cannot read the date/time {text!r}. Use a form such as '2024-12-10 14:30', "
            "'14:30', '2024年12月10日' or '令和6年12月10日'."
        )
    naive = datetime.combine(day, clock)
    if offset is not None:
        return naive.replace(tzinfo=offset)
    if tz is not None:
        return naive.replace(tzinfo=tz)
    return naive.astimezone()


# ---------------------------------------------------------------------------
# Helpers for the result values
# ---------------------------------------------------------------------------


def _utc_offset(dt: datetime) -> str:
    """Return the UTC offset of ``dt`` as +HH:MM."""
    return _format_offset(dt.utcoffset() or timedelta(0))


def _format_offset(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    sign = "-" if minutes < 0 else "+"
    hours, minutes = divmod(abs(minutes), 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


def _timezone_name(dt: datetime) -> str:
    """Return the IANA name if known, otherwise the abbreviation or the offset."""
    key = getattr(dt.tzinfo, "key", None)
    if key:
        return key
    return dt.tzname() or _utc_offset(dt)


def _wall_time_note(dt: datetime) -> str | None:
    """Describe a wall time that is skipped or repeated by a DST change in its timezone."""
    if not isinstance(dt.tzinfo, ZoneInfo):
        return None
    round_trip = dt.astimezone(dt_timezone.utc).astimezone(dt.tzinfo)
    if round_trip.replace(tzinfo=None) != dt.replace(tzinfo=None):
        return (
            f"{dt.strftime('%Y-%m-%d %H:%M')} does not exist in {dt.tzinfo.key} because of a "
            f"daylight saving time change; it was read as {round_trip.strftime('%H:%M')}."
        )
    if dt.replace(fold=0).utcoffset() != dt.replace(fold=1).utcoffset():
        return (
            f"{dt.strftime('%Y-%m-%d %H:%M')} occurs twice in {dt.tzinfo.key} because of a "
            "daylight saving time change; the first occurrence was used."
        )
    return None


def _normalize(dt: datetime) -> datetime:
    """Move a wall time skipped by a DST change to the real time it stands for."""
    if isinstance(dt.tzinfo, ZoneInfo):
        return dt.astimezone(dt_timezone.utc).astimezone(dt.tzinfo)
    return dt


def _weekday_jp(dt: datetime) -> str:
    return _WEEKDAYS_JP[dt.weekday()] + "曜日"


# ---------------------------------------------------------------------------
# Tool logic (plain functions so that they can be tested without MCP)
# ---------------------------------------------------------------------------


def convert_time_result(
    time_text: str,
    target_timezone: str,
    source_timezone: str | None = None,
    format_type: str = "datetime",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Convert ``time_text`` from ``source_timezone`` to ``target_timezone``."""
    pattern = _pattern(format_type)
    target_tz = resolve_timezone(target_timezone)
    if target_tz is None:
        raise ValueError("target_timezone is required, e.g. 'America/New_York'.")
    source = parse_datetime(time_text, resolve_timezone(source_timezone), now)
    note = _wall_time_note(source)
    source = _normalize(source)
    target = source.astimezone(target_tz)
    result: dict[str, Any] = {}
    for key, dt in (("source", source), ("target", target)):
        result[key] = {
            "datetime": _strftime(dt, pattern),
            "timezone": _timezone_name(dt),
            "utc_offset": _utc_offset(dt),
            "day_of_week": dt.strftime("%A"),
            "weekday_jp": _weekday_jp(dt),
        }
    difference = (target.utcoffset() or timedelta(0)) - (source.utcoffset() or timedelta(0))
    result["time_difference"] = _format_offset(difference)
    if note:
        result["note"] = note
    return result


MAX_SHIFT_YEARS = 10000


def shift_datetime_value(
    base: datetime,
    years: int = 0,
    months: int = 0,
    weeks: int = 0,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> datetime:
    """Add the given amounts (negative for the past) to ``base``.

    Years, months, weeks and days move the calendar date and keep the wall time; when the
    day does not exist in the new month, the last day of the month is used (Jan 31 + 1 month
    = Feb 28 or 29). Hours, minutes and seconds are elapsed time, so DST changes are counted.
    """
    if abs(years) > MAX_SHIFT_YEARS or abs(months) > MAX_SHIFT_YEARS * 12:
        raise ValueError(f"Shifts larger than {MAX_SHIFT_YEARS} years are not supported.")
    try:
        total = base.year * 12 + (base.month - 1) + years * 12 + months
        year, month = divmod(total, 12)
        month += 1
        day = min(base.day, calendar.monthrange(year, month)[1])
        shifted = base.replace(year=year, month=month, day=day)
        shifted = _normalize(shifted + timedelta(weeks=weeks, days=days))
        elapsed = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        if elapsed:
            shifted = (shifted.astimezone(dt_timezone.utc) + elapsed).astimezone(shifted.tzinfo)
    except (ValueError, OverflowError) as e:
        raise ValueError("The result is out of the supported range (years 1 to 9999).") from e
    return shifted


def _relative(days: int) -> tuple[str, str]:
    if days == 0:
        return "today", "今日"
    if days > 0:
        return f"in {days} day{'s' if days != 1 else ''}", f"{days}日後"
    return f"{-days} day{'s' if days != -1 else ''} ago", f"{-days}日前"


def datetime_info(
    target: datetime, reference: datetime | None = None, tz: TzInfo | None = None
) -> dict[str, Any]:
    """Return details of ``target`` and its difference from ``reference`` (default: now)."""
    if tz is not None:
        target = target.astimezone(tz)
    if reference is None:
        reference = _now(target.tzinfo)
    reference = reference.astimezone(target.tzinfo)
    dst = target.dst()
    try:
        wareki: str | None = _strftime(target, FORMATS["date_wareki"])
    except ValueError:
        wareki = None
    iso_year, iso_week, _ = target.isocalendar()
    days = (target.date() - reference.date()).days
    relative, relative_jp = _relative(days)
    return {
        "datetime": target.isoformat(timespec="seconds"),
        "date": target.strftime("%Y-%m-%d"),
        "time": target.strftime("%H:%M:%S"),
        "timezone": _timezone_name(target),
        "utc_offset": _utc_offset(target),
        "is_dst": bool(dst),
        "unix_time": int(target.timestamp()),
        "day_of_week": target.strftime("%A"),
        "weekday_jp": _weekday_jp(target),
        "wareki": wareki,
        "day_of_year": target.timetuple().tm_yday,
        "iso_week": f"{iso_year}-W{iso_week:02d}",
        "quarter": (target.month - 1) // 3 + 1,
        "is_leap_year": calendar.isleap(target.year),
        "days_in_month": calendar.monthrange(target.year, target.month)[1],
        "reference": reference.isoformat(timespec="seconds"),
        "days_from_reference": days,
        "seconds_from_reference": int((target - reference).total_seconds()),
        "relative": relative,
        "relative_jp": relative_jp,
    }


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
        raise _tool_error(e) from e


DATETIME_INPUT_HELP = (
    "Accepted forms: '2024-12-10', '2024-12-10 14:30', '2024-12-10T14:30:00+09:00', "
    "'2024/12/10', '2024年12月10日 14時30分', Japanese era such as '令和6年12月10日' or "
    "'R6.12.10', and a time only such as '14:30' (today)."
)


def _tool_error(e: ValueError) -> ToolError:
    # ToolError sends the message to the client as an is_error result.
    return ToolError(str(e))


@mcp.tool(
    name="convert_time",
    description=(
        "Convert a time or date-time from one timezone to another. Returns both sides with "
        "their timezone, UTC offset and weekday, and the time difference. A note is added when "
        "the time is skipped or repeated by a daylight saving time change. " + DATETIME_INPUT_HELP
    ),
)
def convert_time(
    time: Annotated[
        str,
        Field(description="Time or date-time to convert, e.g. '14:30' or '2024-12-10 14:30'."),
    ],
    target_timezone: Annotated[
        str, Field(description="IANA timezone to convert to, e.g. 'America/New_York'.")
    ],
    source_timezone: Annotated[
        str | None,
        Field(
            description="IANA timezone of 'time', e.g. 'Asia/Tokyo'. Omit to use the local "
            "timezone. An offset written in 'time' (+09:00, Z) takes precedence."
        ),
    ] = None,
    format: Annotated[  # noqa: A002 - same name as in get_datetime
        str,
        Field(description="Output format name or custom pattern, as in get_datetime."),
    ] = "datetime",
) -> dict[str, Any]:
    """Convert a time between timezones."""
    try:
        return convert_time_result(time, target_timezone, source_timezone, format)
    except ValueError as e:
        raise _tool_error(e) from e


@mcp.tool(
    name="shift_datetime",
    description=(
        "Add or subtract an amount of time to a date-time (default: now). Use negative "
        "numbers for the past. Years, months, weeks and days keep the wall time; if the day "
        "does not exist in the new month, the last day of that month is used "
        "(2024-01-31 + 1 month = 2024-02-29). Hours, minutes and seconds are elapsed time. "
        + DATETIME_INPUT_HELP
    ),
)
def shift_datetime(
    years: int = 0,
    months: int = 0,
    weeks: int = 0,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
    base: Annotated[
        str | None, Field(description="Start date-time. Omit to start from now.")
    ] = None,
    timezone: Annotated[
        str | None,
        Field(description="IANA timezone of 'base' and of the result. Omit for local time."),
    ] = None,
    format: Annotated[  # noqa: A002 - same name as in get_datetime
        str,
        Field(description="Output format name or custom pattern, as in get_datetime."),
    ] = "datetime",
) -> str:
    """Shift a date-time."""
    try:
        pattern = _pattern(format)
        tz = resolve_timezone(timezone)
        start = _normalize(parse_datetime(base, tz)) if base else _now(tz)
        result = shift_datetime_value(start, years, months, weeks, days, hours, minutes, seconds)
        return _strftime(result, pattern)
    except ValueError as e:
        raise _tool_error(e) from e


@mcp.tool(
    name="get_datetime_info",
    description=(
        "Get details of a date-time (default: now): ISO date-time, timezone, UTC offset, "
        "daylight saving time, Unix time, weekday in English and Japanese, Japanese era "
        "(wareki), day of year, ISO week, quarter, leap year, days in the month, and the "
        "difference from a reference date-time (default: now) in days and seconds, e.g. "
        "how many days until a date. " + DATETIME_INPUT_HELP
    ),
)
def get_datetime_info(
    datetime: Annotated[  # noqa: A002 - public argument name
        str | None, Field(description="Date-time to inspect. Omit for now.")
    ] = None,
    reference: Annotated[
        str | None,
        Field(description="Date-time to compare with. Omit to compare with now."),
    ] = None,
    timezone: Annotated[
        str | None,
        Field(description="IANA timezone for reading and showing the date-times. Omit for local."),
    ] = None,
) -> dict[str, Any]:
    """Get details of a date-time."""
    try:
        tz = resolve_timezone(timezone)
        target = _normalize(parse_datetime(datetime, tz)) if datetime else _now(tz)
        ref = _normalize(parse_datetime(reference, tz)) if reference else None
        return datetime_info(target, ref, tz)
    except ValueError as e:
        raise _tool_error(e) from e


def main() -> None:
    """Run the server over stdio."""
    mcp.run()
