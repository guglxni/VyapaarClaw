"""Indian Financial Calendar & Business Day Computation.

Uses the ``holidays`` library with India-specific calendars to:
- Check if a date is a bank/settlement holiday
- Compute T+N settlement dates (NEFT/RTGS/IMPS)
- List upcoming financial deadlines (GST filing, advance tax, TDS)
- Warn agents about holiday-adjacent payment delays
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

import holidays


_IN_HOLIDAYS = holidays.India(years=range(2024, 2028))

# RBI settlement holidays that go beyond public holidays
_RBI_EXTRA_HOLIDAYS: set[_dt.date] = set()


def is_business_day(date: _dt.date) -> bool:
    """Return True if *date* is a working day (not weekend, not holiday)."""
    if date.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return date not in _IN_HOLIDAYS


def next_business_day(date: _dt.date) -> _dt.date:
    """Return the next business day on or after *date*."""
    current = date
    while not is_business_day(current):
        current += _dt.timedelta(days=1)
    return current


def settlement_date(trade_date: _dt.date, t_plus: int = 2) -> _dt.date:
    """Compute T+N settlement date from *trade_date*.

    Skips weekends and Indian public holidays.
    For NEFT/RTGS, use t_plus=0 (same-day if before cutoff).
    For stock market, use t_plus=1 (T+1 settlement, India since 2024).
    """
    current = trade_date
    days_counted = 0
    while days_counted < t_plus:
        current += _dt.timedelta(days=1)
        if is_business_day(current):
            days_counted += 1
    return next_business_day(current)


def business_days_between(start: _dt.date, end: _dt.date) -> int:
    """Count business days between two dates (exclusive of both)."""
    count = 0
    current = start + _dt.timedelta(days=1)
    while current < end:
        if is_business_day(current):
            count += 1
        current += _dt.timedelta(days=1)
    return count


def upcoming_holidays(from_date: _dt.date | None = None, count: int = 5) -> list[dict[str, Any]]:
    """Return the next *count* holidays from *from_date*."""
    base = from_date or _dt.date.today()
    result: list[dict[str, Any]] = []
    current = base
    while len(result) < count:
        current += _dt.timedelta(days=1)
        if current in _IN_HOLIDAYS:
            result.append({
                "date": current.isoformat(),
                "name": _IN_HOLIDAYS.get(current, "Holiday"),
                "day": current.strftime("%A"),
            })
    return result


# ---------------------------------------------------------------------------
# Indian financial deadlines (recurring)
# ---------------------------------------------------------------------------

_FINANCIAL_DEADLINES = [
    {"day": 7, "name": "TDS Payment (prev month)", "frequency": "monthly"},
    {"day": 11, "name": "GSTR-1 Filing", "frequency": "monthly"},
    {"day": 13, "name": "GSTR-1 (QRMP) Filing", "frequency": "quarterly"},
    {"day": 20, "name": "GSTR-3B Filing", "frequency": "monthly"},
    {"day": 15, "name": "Advance Tax Installment", "frequency": "quarterly",
     "months": [6, 9, 12, 3]},
    {"day": 30, "name": "TDS Return (quarterly)", "frequency": "quarterly",
     "months": [7, 10, 1, 5]},
]


def upcoming_deadlines(
    from_date: _dt.date | None = None,
    count: int = 5,
) -> list[dict[str, Any]]:
    """Return the next *count* financial compliance deadlines."""
    base = from_date or _dt.date.today()
    results: list[dict[str, Any]] = []

    for month_offset in range(6):
        month = base.month + month_offset
        year = base.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1

        for dl in _FINANCIAL_DEADLINES:
            if dl["frequency"] == "quarterly" and "months" in dl:
                if month not in dl["months"]:
                    continue
            try:
                deadline_date = _dt.date(year, month, dl["day"])
            except ValueError:
                continue

            if deadline_date > base:
                results.append({
                    "date": deadline_date.isoformat(),
                    "name": dl["name"],
                    "frequency": dl["frequency"],
                    "is_business_day": is_business_day(deadline_date),
                    "effective_date": next_business_day(deadline_date).isoformat(),
                })

        if len(results) >= count:
            break

    return sorted(results, key=lambda x: x["date"])[:count]
