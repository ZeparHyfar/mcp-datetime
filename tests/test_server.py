from datetime import datetime, timedelta, timezone

import pytest
from mcp import Client

from mcp_datetime.server import FORMATS, format_datetime, mcp

JST = timezone(timedelta(hours=9))
FIXED = datetime(2024, 12, 10, 0, 54, 1, 123456, tzinfo=JST)

# Expected output for every format. The 18 original formats must never change.
EXPECTED = {
    "date": "2024-12-10",
    "date_slash": "2024/12/10",
    "date_jp": "2024年12月10日",
    "datetime": "2024-12-10 00:54:01",
    "datetime_jp": "2024年12月10日 00時54分01秒",
    "datetime_t": "2024-12-10T00:54:01",
    "compact": "20241210005401",
    "compact_date": "20241210",
    "compact_time": "005401",
    "filename_md": "20241210005401.md",
    "filename_txt": "20241210005401.txt",
    "filename_log": "20241210005401.log",
    "iso": "2024-12-10T00:54:01+0900",
    "iso_basic": "20241210T005401+0900",
    "log": "2024-12-10 00:54:01.123456",
    "log_compact": "20241210_005401",
    "time": "00:54:01",
    "time_jp": "00時54分01秒",
    # Added in 0.3.0
    "date_wareki": "令和6年12月10日",
    "datetime_wareki": "令和6年12月10日 00時54分01秒",
    "date_wareki_short": "R6.12.10",
    "date_jp_weekday": "2024年12月10日（火）",
    "datetime_jp_weekday": "2024年12月10日（火） 00時54分01秒",
    "weekday_jp": "火曜日",
}


def test_every_format_has_an_expected_value():
    assert set(FORMATS) == set(EXPECTED)


@pytest.mark.parametrize(("name", "expected"), EXPECTED.items())
def test_format_datetime(name, expected):
    assert format_datetime(name, FIXED) == expected


def test_default_is_current_local_time():
    before = datetime.now().astimezone().replace(microsecond=0)
    result = datetime.strptime(format_datetime("iso"), "%Y-%m-%dT%H:%M:%S%z")
    after = datetime.now().astimezone()
    assert before <= result <= after


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        ("1873-01-01", "明治6年1月1日"),
        ("1912-07-29", "明治45年7月29日"),
        ("1912-07-30", "大正元年7月30日"),
        ("1926-12-24", "大正15年12月24日"),
        ("1926-12-25", "昭和元年12月25日"),
        ("1989-01-07", "昭和64年1月7日"),
        ("1989-01-08", "平成元年1月8日"),
        ("2019-04-30", "平成31年4月30日"),
        ("2019-05-01", "令和元年5月1日"),
    ],
)
def test_wareki_era_boundaries(day, expected):
    now = datetime.fromisoformat(day + "T12:00:00+09:00")
    assert format_datetime("date_wareki", now) == expected


def test_wareki_short_uses_number_for_first_year():
    now = datetime(2019, 5, 1, tzinfo=JST)
    assert format_datetime("date_wareki_short", now) == "R1.5.1"
    assert format_datetime("%Je%JY年", now) == "令和1年"


def test_wareki_before_1873_is_error():
    with pytest.raises(ValueError, match="supported from 1873-01-01"):
        format_datetime("date_wareki", datetime(1872, 12, 31, tzinfo=JST))


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        ("2024-12-09", "月"),
        ("2024-12-10", "火"),
        ("2024-12-11", "水"),
        ("2024-12-12", "木"),
        ("2024-12-13", "金"),
        ("2024-12-14", "土"),
        ("2024-12-15", "日"),
    ],
)
def test_weekday_jp(day, expected):
    now = datetime.fromisoformat(day + "T12:00:00+09:00")
    assert format_datetime("%Ja", now) == expected
    assert format_datetime("weekday_jp", now) == expected + "曜日"


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        ("%Y/%m/%d (%a)", "2024/12/10 (Tue)"),
        ("%-m/%-d %-H:%-M:%-S", "12/10 0:54:1"),
        ("%-I時 %-j日目 %-y年", "12時 345日目 24年"),
        ("%Je%Jy年%-m月%-d日（%Ja）", "令和6年12月10日（火）"),
        ("%G-W%V-%u", "2024-W50-2"),
        ("100%%", "100%"),
        ("no directives but %", "no directives but %"),
    ],
)
def test_custom_pattern(pattern, expected):
    assert format_datetime(pattern, FIXED) == expected


@pytest.mark.parametrize("pattern", ["%Q", "%Jx", "%-Y", "%J"])
def test_custom_pattern_unknown_directive_is_error(pattern):
    with pytest.raises(ValueError, match="Unknown directive"):
        format_datetime(pattern, FIXED)


def test_custom_pattern_too_long_is_error():
    with pytest.raises(ValueError, match="longer than 200"):
        format_datetime("%Y" * 101, FIXED)


@pytest.mark.parametrize(
    ("tz", "name", "expected"),
    [
        ("UTC", "iso", "2024-12-09T15:54:01+0000"),
        ("UTC", "date", "2024-12-09"),
        ("America/New_York", "iso", "2024-12-09T10:54:01-0500"),
        ("Asia/Tokyo", "iso", "2024-12-10T00:54:01+0900"),
        ("Europe/London", "%Z", "GMT"),
    ],
)
def test_timezone(tz, name, expected):
    assert format_datetime(name, FIXED, timezone=tz) == expected


def test_timezone_for_current_time():
    assert format_datetime("%z", timezone="Asia/Tokyo") == "+0900"
    assert format_datetime("%z", timezone="UTC") == "+0000"


@pytest.mark.parametrize(
    "tz", ["Mars/Olympus", "../etc/passwd", "JST\nINFO:fake", "C:\\Windows", "Asia//Tokyo", "a" * 300]
)
def test_unknown_timezone_is_error(tz):
    with pytest.raises(ValueError, match="Unknown timezone") as exc_info:
        format_datetime("date", FIXED, timezone=tz)
    assert "\n" not in str(exc_info.value)


def test_unknown_format_message_is_single_line():
    with pytest.raises(ValueError) as exc_info:
        format_datetime("bad\nINFO:fake")
    message = str(exc_info.value)
    assert "\n" not in message
    assert "'bad\\nINFO:fake'" in message


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_tool_is_listed_with_format_argument():
    async with Client(mcp) as client:
        tools = (await client.list_tools()).tools
    assert [t.name for t in tools] == [
        "get_datetime",
        "convert_time",
        "shift_datetime",
        "get_datetime_info",
    ]
    tool = tools[0]
    assert tool.input_schema["required"] == ["format"]
    assert "timezone" in tool.input_schema["properties"]
    for name in FORMATS:
        assert f"- {name}: " in tool.description


@pytest.mark.anyio
async def test_call_tool():
    async with Client(mcp) as client:
        result = await client.call_tool("get_datetime", {"format": "compact_date"})
    assert not result.is_error
    assert result.content[0].text == datetime.now().astimezone().strftime("%Y%m%d")


@pytest.mark.anyio
async def test_call_tool_unknown_format_is_error():
    async with Client(mcp) as client:
        result = await client.call_tool("get_datetime", {"format": "nope"})
    assert result.is_error
    assert "Unknown format type: 'nope'" in result.content[0].text


@pytest.mark.anyio
async def test_call_tool_with_pattern_and_timezone():
    async with Client(mcp) as client:
        result = await client.call_tool("get_datetime", {"format": "%z", "timezone": "UTC"})
    assert not result.is_error
    assert result.content[0].text == "+0000"


@pytest.mark.anyio
async def test_call_tool_unknown_timezone_is_error():
    async with Client(mcp) as client:
        result = await client.call_tool("get_datetime", {"format": "date", "timezone": "Nowhere"})
    assert result.is_error
    assert "Unknown timezone: 'Nowhere'" in result.content[0].text
