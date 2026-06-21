"""Test du chargement d'un fichier .env jusqu'à la configuration."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from apk_stats.config import AppConfig

ENV_CONTENT = (
    "GOOGLE_APPLICATION_CREDENTIALS=/keys/sa.json\n"
    "EDM_BUCKET_NAME=pubsite_prod_1\n"
    "EDM_PACKAGES=com.incubuo.mbem\n"
    "EDM_COUNTRIES=BF,CI\n"
    "EDM_START_PERIOD=2026-01\n"
    "EDM_END_PERIOD=2026-01\n"
)


def test_env_file_feeds_config(tmp_path, monkeypatch):
    env_file = tmp_path / "custom.env"
    env_file.write_text(ENV_CONTENT, encoding="utf-8")

    # Isole l'environnement du processus : monkeypatch restaure l'original ensuite.
    monkeypatch.setattr(os, "environ", {})
    load_dotenv(env_file)

    config = AppConfig.from_env()

    assert config.bucket_name == "pubsite_prod_1"
    assert config.packages == ("com.incubuo.mbem",)
    assert config.countries == ("BF", "CI")
    assert config.credentials_path == "/keys/sa.json"


def test_os_environ_takes_precedence_over_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / "custom.env"
    env_file.write_text(ENV_CONTENT, encoding="utf-8")

    monkeypatch.setattr(os, "environ", {"EDM_COUNTRIES": "ML"})
    load_dotenv(env_file)  # n'écrase pas une variable déjà définie

    config = AppConfig.from_env()
    assert config.countries == ("ML",)
