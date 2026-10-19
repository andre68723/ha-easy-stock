"""Decide whether an asset has traded today, from Yahoo's intraday bars.

Three rules were tried before this one, and all three read the **quote** —
``regularMarketPrice`` against the last daily close, then ``regularMarketTime``.
Both fail for currency pairs over a weekend, because Yahoo refreshes the quote
while the candle series stands still. Measured on Sunday 2026-10-18 for
``CHF=X``: at 20:34 Berlin the quote was Friday's, two days old; at 22:34 the
price had moved and the timestamp was 14 minutes old — yet the newest hourly bar
was still Friday 20:00 UTC and ``currentTradingPeriod`` still described the
Friday session. The refresh lands at an unpredictable hour (20:29 one weekend,
22:11 the next), and ``GC=F``, ``^NDX`` and ``ALV.DE`` show no such split.

A bar with a real price is the trade itself, so that is what this asks about.
"""
from datetime import date, datetime, timezone


def traded_on(result: dict, day: date, tzinfo) -> bool:
    """True if the intraday series holds a bar with a price on `day` in `tzinfo`.

    Bars whose close is ``null`` are placeholders — Yahoo emits them over a
    weekend (six of them for ``GC=F`` on a Saturday) — and are not trades.
    A payload without a usable series answers False; the caller decides what to
    do with that rather than being handed a guess.
    """
    if not isinstance(result, dict):
        return False

    timestamps = result.get("timestamp") or []
    quotes = (result.get("indicators") or {}).get("quote") or []
    closes = (quotes[0] or {}).get("close") or [] if quotes else []

    for ts, close in zip(timestamps, closes):
        if ts is None or close is None:
            continue
        if datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(tzinfo).date() == day:
            return True
    return False
