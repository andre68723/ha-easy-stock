"""Deciding "has this traded today" from actual intraday bars.

Yahoo refreshes the top-level quote for FX pairs during the weekend while the
candle series stays stale — measured on 2026-10-18, when `regularMarketTime`
jumped to a timestamp 14 minutes old while the newest hourly bar was still the
previous Friday. Every rule built on the quote (its price or its timestamp)
misfires at that moment; the bars do not.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from custom_components.easy_stock.intraday import traded_on

BERLIN = ZoneInfo("Europe/Berlin")
LONDON = ZoneInfo("Europe/London")


def _result(*bars):
    """Build a chart result from (datetime, close) pairs, close None = placeholder."""
    return {
        "timestamp": [int(dt.timestamp()) for dt, _ in bars],
        "indicators": {"quote": [{"close": [c for _, c in bars]}]},
    }


def test_a_bar_with_a_price_today_counts_as_traded():
    day = datetime(2026, 10, 19, 10, 0, tzinfo=BERLIN)
    result = _result((day, 0.8253))
    assert traded_on(result, day.date(), BERLIN) is True


def test_placeholder_bars_without_a_price_do_not_count():
    # Yahoo emits null-close bars over a weekend — six of them for GC=F on a
    # Saturday. They are not trades.
    day = datetime(2026, 10, 17, 10, 0, tzinfo=BERLIN)
    result = _result((day, None), (day.replace(hour=11), None))
    assert traded_on(result, day.date(), BERLIN) is False


def test_the_weekend_case_that_broke_every_quote_based_rule():
    # Sunday 18.10. 22:34 Berlin: the newest bar is still Friday 20:00 UTC,
    # even though the quote had just been refreshed.
    friday = datetime(2026, 10, 16, 22, 0, tzinfo=BERLIN)
    sunday = datetime(2026, 10, 18, 22, 34, tzinfo=BERLIN)
    result = _result((friday, 0.82361))
    assert traded_on(result, sunday.date(), BERLIN) is False


def test_a_bar_from_late_yesterday_in_utc_belongs_to_today_in_berlin():
    # 23:30 UTC is already 01:30 the next day in Berlin.
    bar = datetime(2026, 11, 10, 0, 30, tzinfo=BERLIN)
    assert traded_on(_result((bar, 1.0)), bar.date(), BERLIN) is True
    # ...and not to the day before
    assert traded_on(_result((bar, 1.0)), datetime(2026, 11, 9, tzinfo=BERLIN).date(), BERLIN) is False


def test_the_day_is_read_in_the_timezone_handed_in():
    # 00:30 Berlin is still the previous day in London.
    bar = datetime(2026, 11, 10, 0, 30, tzinfo=BERLIN)
    assert traded_on(_result((bar, 1.0)), datetime(2026, 11, 9, tzinfo=LONDON).date(), LONDON) is True


@pytest.mark.parametrize(
    "result",
    [
        {},
        {"timestamp": [], "indicators": {"quote": [{"close": []}]}},
        {"timestamp": [1792354840]},
        {"timestamp": [1792354840], "indicators": {"quote": []}},
        {"indicators": {"quote": [{"close": [1.0]}]}},
    ],
)
def test_a_payload_without_usable_bars_is_false(result):
    assert traded_on(result, datetime(2026, 10, 19, tzinfo=BERLIN).date(), BERLIN) is False
