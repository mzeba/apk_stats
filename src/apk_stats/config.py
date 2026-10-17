"""Configuration applicative, chargée et validée depuis l'environnement.

Aucun secret ni valeur d'infrastructure n'est codé en dur : tout provient de
variables d'environnement, ce qui sépare la configuration du code (12-factor).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping

from apk_stats.exceptions import ConfigError
from apk_stats.models import DateRange, Frequency, Period

# Un nom de package Android valide : segments alphanumériques séparés par des points.
# Sert aussi de garde-fou contre l'injection dans les chemins d'objets GCS.
_PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$")

# Code pays ISO 3166-1 alpha-2 (deux lettres).
_COUNTRY_RE = re.compile(r"^[A-Za-z]{2}$")

# Variable d'environnement standard reconnue par les bibliothèques Google Cloud.
ENV_CREDENTIALS = "GOOGLE_APPLICATION_CREDENTIALS"
ENV_BUCKET = "EDM_BUCKET_NAME"
ENV_PACKAGES = "EDM_PACKAGES"
ENV_COUNTRIES = "EDM_COUNTRIES"
ENV_START = "EDM_START_PERIOD"
ENV_END = "EDM_END_PERIOD"
ENV_OUTPUT = "EDM_OUTPUT"
ENV_FREQUENCY = "EDM_FREQUENCY"

DEFAULT_OUTPUT = "stats_mensuelles_burkina_vs_monde.csv"


@dataclass(frozen=True)
class AppConfig:
    """Paramètres d'exécution validés et immutables."""

    credentials_path: str
    bucket_name: str
    packages: tuple[str, ...]
    countries: tuple[str, ...]
    date_range: DateRange
    output_path: str
    frequency: Frequency = Frequency.MONTHLY

    @property
    def periods(self) -> list[Period]:
        """Périodes mensuelles touchées par l'intervalle configuré."""
        return self.date_range.periods

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        credentials_path: str | None = None,
        bucket_name: str | None = None,
        packages: str | None = None,
        countries: str | None = None,
        start: str | None = None,
        end: str | None = None,
        output_path: str | None = None,
        frequency: str | None = None,
    ) -> "AppConfig":
        """Construit la configuration depuis l'environnement.

        Les arguments nommés (issus de la CLI) prennent le pas sur l'environnement
        lorsqu'ils sont fournis. Lève :class:`ConfigError` si un champ requis manque
        ou est invalide.
        """
        env = os.environ if env is None else env

        resolved_credentials = credentials_path or env.get(ENV_CREDENTIALS)
        resolved_bucket = bucket_name or env.get(ENV_BUCKET)
        resolved_packages = packages or env.get(ENV_PACKAGES)
        resolved_countries = countries or env.get(ENV_COUNTRIES)
        resolved_start = start or env.get(ENV_START)
        resolved_end = end or env.get(ENV_END)
        resolved_output = output_path or env.get(ENV_OUTPUT) or DEFAULT_OUTPUT
        resolved_frequency = frequency or env.get(ENV_FREQUENCY)

        return cls(
            credentials_path=_require(resolved_credentials, ENV_CREDENTIALS),
            bucket_name=_validate_bucket(_require(resolved_bucket, ENV_BUCKET)),
            packages=_parse_packages(_require(resolved_packages, ENV_PACKAGES)),
            countries=_parse_countries(_require(resolved_countries, ENV_COUNTRIES)),
            date_range=DateRange.parse(
                _require(resolved_start, ENV_START),
                _require(resolved_end, ENV_END),
            ),
            output_path=resolved_output,
            frequency=(
                Frequency.parse(resolved_frequency)
                if resolved_frequency
                else Frequency.MONTHLY
            ),
        )


def _require(value: str | None, name: str) -> str:
    if not value:
        raise ConfigError(
            f"Configuration manquante : {name}. "
            f"Définissez la variable d'environnement ou passez l'option CLI."
        )
    return value


def _validate_bucket(value: str) -> str:
    value = value.strip()
    if "XXXXXXXX" in value.upper():
        raise ConfigError(
            f"Le nom de bucket ({value!r}) est un gabarit non configuré."
        )
    return value


def _parse_packages(raw: str) -> tuple[str, ...]:
    packages = tuple(p.strip() for p in raw.split(",") if p.strip())
    if not packages:
        raise ConfigError("Aucun package fourni.")
    invalid = [p for p in packages if not _PACKAGE_RE.match(p)]
    if invalid:
        raise ConfigError(
            f"Nom(s) de package invalide(s) : {', '.join(invalid)}. "
            f"Format attendu de type 'com.exemple.app'."
        )
    return packages


def _parse_countries(raw: str) -> tuple[str, ...]:
    codes = [c.strip().upper() for c in raw.split(",") if c.strip()]
    if not codes:
        raise ConfigError("Aucun pays fourni.")
    invalid = [c for c in codes if not _COUNTRY_RE.match(c)]
    if invalid:
        raise ConfigError(
            f"Code(s) pays invalide(s) : {', '.join(invalid)}. "
            f"Attendu : code ISO 3166-1 alpha-2 (deux lettres), ex. 'BF'."
        )
    # Dé-duplication en conservant l'ordre de la liste.
    return tuple(dict.fromkeys(codes))
