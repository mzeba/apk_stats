"""Tests de la logique d'agrégation géographique (pays configurables)."""

from __future__ import annotations

import pytest

from apk_stats.aggregator import Aggregator
from apk_stats.exceptions import ConfigError
from apk_stats.models import CountryInstall

PERIOD = "2026-01"


def _records(*pairs: tuple[str, int]) -> list[CountryInstall]:
    return [CountryInstall(country_code=c, installs=n) for c, n in pairs]


def test_world_is_sum_of_all_countries(aggregator: Aggregator):
    result = aggregator.aggregate(
        "com.x", PERIOD, _records(("BF", 5), ("FR", 3), ("CI", 2))
    )
    assert result.world == 10


def test_targets_counted_per_country(aggregator: Aggregator):
    result = aggregator.aggregate(
        "com.x", PERIOD, _records(("BF", 5), ("CI", 2), ("FR", 3))
    )
    assert result.by_country == {"BF": 5, "CI": 2}


def test_listed_country_absent_from_report_is_zero(aggregator: Aggregator):
    result = aggregator.aggregate("com.x", PERIOD, _records(("BF", 5)))
    assert result.by_country == {"BF": 5, "CI": 0}


def test_country_outside_list_only_in_world(aggregator: Aggregator):
    result = aggregator.aggregate("com.x", PERIOD, _records(("FR", 7)))
    assert result.by_country == {"BF": 0, "CI": 0}
    assert result.world == 7


def test_country_code_case_is_normalised(aggregator: Aggregator):
    result = aggregator.aggregate("com.x", PERIOD, _records(("bf", 4)))
    assert result.by_country["BF"] == 4


def test_by_country_preserves_configured_order():
    aggregator = Aggregator(("CI", "BF", "ML"))
    result = aggregator.aggregate("com.x", PERIOD, _records(("BF", 1)))
    assert list(result.by_country.keys()) == ["CI", "BF", "ML"]


def test_no_records_yields_zeroes(aggregator: Aggregator):
    result = aggregator.aggregate("com.x", PERIOD, [])
    assert result.by_country == {"BF": 0, "CI": 0}
    assert result.world == 0


def test_target_countries_deduplicated_and_uppercased():
    aggregator = Aggregator(("bf", "BF", "ci"))
    assert aggregator.target_countries == ("BF", "CI")


def test_empty_target_list_rejected():
    with pytest.raises(ConfigError):
        Aggregator(())
