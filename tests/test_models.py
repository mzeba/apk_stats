"""Tests des objets-valeur du domaine."""

from __future__ import annotations

import pytest

from apk_stats.exceptions import ConfigError
from apk_stats.models import Period


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
