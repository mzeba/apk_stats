"""Tests des objets-valeur du domaine."""

from __future__ import annotations

import pytest

from datetime import date

from apk_stats.exceptions import ConfigError
from apk_stats.models import DateRange, Frequency, Period


def test_period_parse_and_format():
    period = Period.parse("2026-01")
    assert (period.year, period.month) == (2026, 1)
    assert period.yyyymm == "202601"
    assert str(period) == "2026-01"


@pytest.mark.parametrize("value", ["2026/01", "26-1", "2026-13", "", "abc"])
def test_period_parse_rejects_invalid(value):
    with pytest.raises(ConfigError):
        Period.parse(value)


def test_period_range_crosses_year_boundary():
    periods = Period.range(Period.parse("2025-11"), Period.parse("2026-02"))
    assert [p.yyyymm for p in periods] == ["202511", "202512", "202601", "202602"]


def test_period_range_single_month():
    periods = Period.range(Period.parse("2026-03"), Period.parse("2026-03"))
    assert [str(p) for p in periods] == ["2026-03"]


def test_period_range_rejects_reversed_bounds():
    with pytest.raises(ConfigError):
        Period.range(Period.parse("2026-05"), Period.parse("2026-01"))


def test_period_is_ordered():
    assert Period.parse("2026-01") < Period.parse("2026-02")


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        ("2026", "2026", (date(2026, 1, 1), date(2026, 12, 31))),
        ("2026-02", "2026-02", (date(2026, 2, 1), date(2026, 2, 28))),
        ("2024-02", "2024-02", (date(2024, 2, 1), date(2024, 2, 29))),
        ("2026-03-15", "2026-04-02", (date(2026, 3, 15), date(2026, 4, 2))),
        ("2025", "2026-01-10", (date(2025, 1, 1), date(2026, 1, 10))),
    ],
)
def test_date_range_parse_accepts_all_formats(start, end, expected):
    date_range = DateRange.parse(start, end)
    assert (date_range.start, date_range.end) == expected


@pytest.mark.parametrize(
    "value", ["26", "2026-1", "2026-13", "2026-02-30", "2026-01-1", "2026/01/01", "0000", ""]
)
def test_date_range_parse_rejects_invalid(value):
    with pytest.raises(ConfigError):
        DateRange.parse(value, "2030")


def test_date_range_rejects_reversed_bounds():
    with pytest.raises(ConfigError):
        DateRange.parse("2026-03-10", "2026-03-09")


def test_date_range_periods_and_coverage():
    date_range = DateRange.parse("2026-01-10", "2026-03")
    assert [str(p) for p in date_range.periods] == ["2026-01", "2026-02", "2026-03"]
    assert not date_range.covers(Period.parse("2026-01"))
    assert date_range.covers(Period.parse("2026-02"))
    assert date_range.covers(Period.parse("2026-03"))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("yearly", Frequency.YEARLY),
        ("Monthly", Frequency.MONTHLY),
        (" daily ", Frequency.DAILY),
    ],
)
def test_frequency_parse(value, expected):
    assert Frequency.parse(value) is expected


@pytest.mark.parametrize("value", ["weekly", "mensuelle", "journalière", ""])
def test_frequency_parse_rejects_unknown(value):
    with pytest.raises(ConfigError):
        Frequency.parse(value)
