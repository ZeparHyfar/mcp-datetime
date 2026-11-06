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
    assert [t.name for t in tools] == ["get_datetime"]
    tool = tools[0]
    assert tool.input_schema["required"] == ["format"]
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
