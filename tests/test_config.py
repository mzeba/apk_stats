"""Tests du chargement et de la validation de la configuration."""

from __future__ import annotations

import pytest

from apk_stats.config import AppConfig
from apk_stats.exceptions import ConfigError
from apk_stats.models import Frequency

BASE_ENV = {
    "GOOGLE_APPLICATION_CREDENTIALS": "/keys/sa.json",
    "EDM_BUCKET_NAME": "pubsite_prod_123",
    "EDM_PACKAGES": "com.incubuo.mbem,com.incubuo.meg",
    "EDM_COUNTRIES": "BF,CI",
    "EDM_START_PERIOD": "2026-01",
    "EDM_END_PERIOD": "2026-03",
}


def test_loads_from_env():
    config = AppConfig.from_env(BASE_ENV)
    assert config.credentials_path == "/keys/sa.json"
    assert config.packages == ("com.incubuo.mbem", "com.incubuo.meg")
    assert config.countries == ("BF", "CI")
    assert [str(p) for p in config.periods] == ["2026-01", "2026-02", "2026-03"]


def test_countries_normalised_and_deduplicated():
    env = {**BASE_ENV, "EDM_COUNTRIES": "bf, CI ,bf"}
    config = AppConfig.from_env(env)
    assert config.countries == ("BF", "CI")


@pytest.mark.parametrize("countries", ["BFA", "B", "12", "B1", "", ","])
def test_invalid_country_codes_rejected(countries):
    env = {**BASE_ENV, "EDM_COUNTRIES": countries}
    with pytest.raises(ConfigError):
        AppConfig.from_env(env)


def test_cli_overrides_take_precedence():
    config = AppConfig.from_env(BASE_ENV, bucket_name="override-bucket", output_path="out.csv")
    assert config.bucket_name == "override-bucket"
    assert config.output_path == "out.csv"


@pytest.mark.parametrize("missing", list(BASE_ENV))
def test_missing_required_field_raises(missing):
    env = {k: v for k, v in BASE_ENV.items() if k != missing}
    with pytest.raises(ConfigError):
        AppConfig.from_env(env)


@pytest.mark.parametrize("package", ["evilpackage", "com x", "../etc", "a.b c"])
def test_invalid_package_names_rejected(package):
    env = {**BASE_ENV, "EDM_PACKAGES": package}
    with pytest.raises(ConfigError):
        AppConfig.from_env(env)


def test_placeholder_bucket_rejected():
    env = {**BASE_ENV, "EDM_BUCKET_NAME": "pubsite_prod_XXXXXXXXXXXX"}
    with pytest.raises(ConfigError):
        AppConfig.from_env(env)


def test_default_output_when_unset():
    config = AppConfig.from_env(BASE_ENV)
    assert config.output_path == "stats_mensuelles_burkina_vs_monde.csv"


def test_day_and_year_bounds_accepted():
    env = {**BASE_ENV, "EDM_START_PERIOD": "2025-12-15", "EDM_END_PERIOD": "2026"}
    config = AppConfig.from_env(env)
    assert str(config.date_range) == "2025-12-15 → 2026-12-31"
    assert len(config.periods) == 13


def test_frequency_defaults_to_monthly():
    assert AppConfig.from_env(BASE_ENV).frequency is Frequency.MONTHLY


def test_frequency_from_env_and_cli_override():
    env = {**BASE_ENV, "EDM_FREQUENCY": "yearly"}
    assert AppConfig.from_env(env).frequency is Frequency.YEARLY
    assert AppConfig.from_env(env, frequency="daily").frequency is Frequency.DAILY


def test_invalid_frequency_rejected():
    with pytest.raises(ConfigError):
        AppConfig.from_env({**BASE_ENV, "EDM_FREQUENCY": "weekly"})
