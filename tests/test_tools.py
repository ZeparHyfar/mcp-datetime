"""Tests for parse_datetime, convert_time, shift_datetime and get_datetime_info."""

import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from mcp import Client

from mcp_datetime.server import (
    convert_time_result,
    datetime_info,
    mcp,
    parse_datetime,
    shift_datetime_value,
)

TOKYO = ZoneInfo("Asia/Tokyo")
NEW_YORK = ZoneInfo("America/New_York")
NOW = datetime(2024, 12, 10, 9, 0, tzinfo=TOKYO)


# --- parse_datetime -------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2024-12-10", "2024-12-10T00:00:00+09:00"),
        ("2024/12/10 14:30", "2024-12-10T14:30:00+09:00"),
        ("2024-12-10T14:30:05", "2024-12-10T14:30:05+09:00"),
        ("2024-12-10T14:30:05.5+05:30", "2024-12-10T14:30:05.500000+05:30"),
        ("2024-12-10T14:30Z", "2024-12-10T14:30:00+00:00"),
        ("2024-12-10 14:30 -0500", "2024-12-10T14:30:00-05:00"),
        ("2024年12月10日", "2024-12-10T00:00:00+09:00"),
        ("2024年12月10日 14時30分", "2024-12-10T14:30:00+09:00"),
        ("2024年12月10日 14時30分05秒", "2024-12-10T14:30:05+09:00"),
        ("令和6年12月10日", "2024-12-10T00:00:00+09:00"),
        ("令和元年5月1日 9:05", "2019-05-01T09:05:00+09:00"),
        ("R6.12.10", "2024-12-10T00:00:00+09:00"),
        ("r1.5.1", "2019-05-01T00:00:00+09:00"),
        ("H31.4.30", "2019-04-30T00:00:00+09:00"),
        ("平成元年1月8日", "1989-01-08T00:00:00+09:00"),
        ("昭和64年1月7日", "1989-01-07T00:00:00+09:00"),
        # Before 1888 Tokyo used local mean time (+09:18:59) in the tz database.
        ("明治6年1月1日", "1873-01-01T00:00:00+09:18:59"),
        ("㍻31年4月30日", "2019-04-30T00:00:00+09:00"),
        ("２０２４－１２－１０", "2024-12-10T00:00:00+09:00"),
        ("14:30", "2024-12-10T14:30:00+09:00"),
        ("１４：３０", "2024-12-10T14:30:00+09:00"),
        ("14:30:15", "2024-12-10T14:30:15+09:00"),
    ],
)
def test_parse_datetime(text, expected):
    assert parse_datetime(text, TOKYO, NOW).isoformat() == expected


def test_parse_time_only_uses_today_in_the_timezone():
    # 2024-12-10 09:00 in Tokyo is still 2024-12-09 in New York.
    assert parse_datetime("14:30", NEW_YORK, NOW).isoformat() == "2024-12-09T14:30:00-05:00"


def test_parse_without_timezone_uses_local_time():
    result = parse_datetime("2024-12-10 14:30", None)
    assert result.tzinfo is not None
    assert result.replace(tzinfo=None) == datetime(2024, 12, 10, 14, 30)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("平成31年5月1日", "does not exist"),
        ("令和元年4月30日", "does not exist"),
        ("昭和65年1月1日", "does not exist"),
        ("令和0年1月1日", "does not exist"),
        ("明治5年1月1日", "supported from 1873-01-01"),
        ("R7.13.1", "not a valid date"),
        ("2024-02-30", "not a valid date"),
        ("25:00", "not a valid time"),
        ("12:60", "not a valid time"),
        ("hello", "Cannot read"),
        ("2024-12-10\nINFO:fake", "Cannot read"),
        ("1" * 101, "longer than 100"),
    ],
)
def test_parse_datetime_errors(text, message):
    with pytest.raises(ValueError, match=message) as exc_info:
        parse_datetime(text, TOKYO, NOW)
    assert "\n" not in str(exc_info.value)


# --- convert_time ---------------------------------------------------------


def test_convert_time():
    result = convert_time_result("2024-12-10 14:30", "America/New_York", "Asia/Tokyo")
    assert result == {
        "source": {
            "datetime": "2024-12-10 14:30:00",
            "timezone": "Asia/Tokyo",
            "utc_offset": "+09:00",
            "day_of_week": "Tuesday",
            "weekday_jp": "火曜日",
        },
        "target": {
            "datetime": "2024-12-10 00:30:00",
            "timezone": "America/New_York",
            "utc_offset": "-05:00",
            "day_of_week": "Tuesday",
            "weekday_jp": "火曜日",
        },
        "time_difference": "-14:00",
    }


def test_convert_time_half_hour_offset_and_format():
    result = convert_time_result("09:00", "Asia/Kolkata", "Asia/Tokyo", "%H:%M", now=NOW)
    assert result["source"]["datetime"] == "09:00"
    assert result["target"]["datetime"] == "05:30"
    assert result["time_difference"] == "-03:30"


def test_convert_time_offset_in_input_wins():
    result = convert_time_result("2024-12-10T00:00Z", "Asia/Tokyo", "America/New_York")
    assert result["target"]["datetime"] == "2024-12-10 09:00:00"


def test_convert_time_skipped_wall_time_has_note():
    result = convert_time_result("2025-03-09 02:30", "UTC", "America/New_York")
    assert result["source"]["datetime"] == "2025-03-09 03:30:00"
    assert result["target"]["datetime"] == "2025-03-09 07:30:00"
    assert "does not exist" in result["note"]


def test_convert_time_repeated_wall_time_has_note():
    result = convert_time_result("2025-11-02 01:30", "UTC", "America/New_York")
    assert result["target"]["datetime"] == "2025-11-02 05:30:00"
    assert "occurs twice" in result["note"]


def test_convert_time_requires_target():
    with pytest.raises(ValueError, match="target_timezone is required"):
        convert_time_result("14:30", "")


# --- shift_datetime -------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"days": 1}, "2024-02-01T10:00:00+09:00"),
        ({"days": -31}, "2023-12-31T10:00:00+09:00"),
        ({"weeks": 2}, "2024-02-14T10:00:00+09:00"),
        ({"months": 1}, "2024-02-29T10:00:00+09:00"),
        ({"months": 13}, "2025-02-28T10:00:00+09:00"),
        ({"months": -2}, "2023-11-30T10:00:00+09:00"),
        ({"years": 1, "months": 1}, "2025-02-28T10:00:00+09:00"),
        ({"hours": -11}, "2024-01-30T23:00:00+09:00"),
        ({"minutes": 90, "seconds": 30}, "2024-01-31T11:30:30+09:00"),
    ],
)
def test_shift_datetime(kwargs, expected):
    base = datetime(2024, 1, 31, 10, 0, tzinfo=TOKYO)
    assert shift_datetime_value(base, **kwargs).isoformat() == expected


def test_shift_across_dst_days_keep_wall_time_hours_are_elapsed():
    base = datetime(2025, 3, 8, 12, 0, tzinfo=NEW_YORK)
    assert shift_datetime_value(base, days=1).isoformat() == "2025-03-09T12:00:00-04:00"
    assert shift_datetime_value(base, hours=24).isoformat() == "2025-03-09T13:00:00-04:00"


def test_shift_into_skipped_wall_time_moves_forward():
    base = datetime(2025, 3, 8, 2, 30, tzinfo=NEW_YORK)
    assert shift_datetime_value(base, days=1).isoformat() == "2025-03-09T03:30:00-04:00"


@pytest.mark.parametrize("kwargs", [{"years": 20000}, {"years": 9000}, {"days": 10**7}])
def test_shift_out_of_range_is_error(kwargs):
    base = datetime(2024, 1, 31, tzinfo=TOKYO)
    with pytest.raises(ValueError):
        shift_datetime_value(base, **kwargs)


# --- get_datetime_info ----------------------------------------------------


def test_datetime_info():
    target = datetime(2024, 12, 25, 0, 0, tzinfo=TOKYO)
    info = datetime_info(target, NOW)
    assert info == {
        "datetime": "2024-12-25T00:00:00+09:00",
        "date": "2024-12-25",
        "time": "00:00:00",
        "timezone": "Asia/Tokyo",
        "utc_offset": "+09:00",
        "is_dst": False,
        "unix_time": 1735052400,
        "day_of_week": "Wednesday",
        "weekday_jp": "水曜日",
        "wareki": "令和6年12月25日",
        "day_of_year": 360,
        "iso_week": "2024-W52",
        "quarter": 4,
        "is_leap_year": True,
        "days_in_month": 31,
        "reference": "2024-12-10T09:00:00+09:00",
        "days_from_reference": 15,
        "seconds_from_reference": 1263600,
        "relative": "in 15 days",
        "relative_jp": "15日後",
    }


@pytest.mark.parametrize(
    ("day", "days", "relative", "relative_jp"),
    [
        ("2024-12-10T23:59:00", 0, "today", "今日"),
        ("2024-12-11T00:00:00", 1, "in 1 day", "1日後"),
        ("2024-12-09T23:00:00", -1, "1 day ago", "1日前"),
        ("2024-12-07T12:00:00", -3, "3 days ago", "3日前"),
    ],
)
def test_datetime_info_relative(day, days, relative, relative_jp):
    info = datetime_info(datetime.fromisoformat(day).replace(tzinfo=TOKYO), NOW)
    assert (info["days_from_reference"], info["relative"], info["relative_jp"]) == (
        days,
        relative,
        relative_jp,
    )


def test_datetime_info_dst_and_old_date():
    summer = datetime_info(datetime(2025, 7, 1, 12, tzinfo=NEW_YORK), NOW)
    assert summer["is_dst"] is True
    assert summer["utc_offset"] == "-04:00"
    old = datetime_info(datetime(1872, 1, 1, tzinfo=timezone(timedelta(hours=9))), NOW)
    assert old["wareki"] is None
    assert old["timezone"] == "UTC+09:00"


# --- MCP calls ------------------------------------------------------------


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _call(name, arguments):
    async with Client(mcp) as client:
        return await client.call_tool(name, arguments)


@pytest.mark.anyio
async def test_call_convert_time():
    result = await _call(
        "convert_time",
        {"time": "2024-12-10 14:30", "source_timezone": "Asia/Tokyo",
         "target_timezone": "Europe/London", "format": "datetime_jp"},
    )
    assert not result.is_error
    data = json.loads(result.content[0].text)
    assert data["target"]["datetime"] == "2024年12月10日 05時30分00秒"


@pytest.mark.anyio
async def test_call_shift_datetime():
    result = await _call(
        "shift_datetime",
        {"base": "令和6年1月31日 10:00", "months": 1, "timezone": "Asia/Tokyo",
         "format": "datetime_wareki"},
    )
    assert not result.is_error
    assert result.content[0].text == "令和6年2月29日 10時00分00秒"


@pytest.mark.anyio
async def test_call_shift_datetime_from_now():
    result = await _call("shift_datetime", {"days": 1, "timezone": "UTC", "format": "date"})
    expected = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    assert result.content[0].text == expected


@pytest.mark.anyio
async def test_call_get_datetime_info():
    result = await _call(
        "get_datetime_info",
        {"datetime": "2024-12-25", "reference": "2024-12-10", "timezone": "Asia/Tokyo"},
    )
    assert not result.is_error
    data = json.loads(result.content[0].text)
    assert data["days_from_reference"] == 15
    assert data["wareki"] == "令和6年12月25日"


@pytest.mark.anyio
async def test_call_get_datetime_info_now():
    result = await _call("get_datetime_info", {"timezone": "UTC"})
    data = json.loads(result.content[0].text)
    assert data["relative"] == "today"
    assert data["timezone"] == "UTC"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("name", "arguments", "message"),
    [
        ("convert_time", {"time": "nope", "target_timezone": "UTC"}, "Cannot read"),
        ("convert_time", {"time": "14:30", "target_timezone": "Nowhere"}, "Unknown timezone"),
        ("shift_datetime", {"base": "平成31年5月1日"}, "does not exist"),
        ("shift_datetime", {"days": 1, "format": "nope"}, "Unknown format type"),
        ("get_datetime_info", {"datetime": "2024-02-30"}, "not a valid date"),
    ],
)
async def test_call_errors(name, arguments, message):
    result = await _call(name, arguments)
    assert result.is_error
    assert message in result.content[0].text
