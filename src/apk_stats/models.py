"""Objets-valeur immutables du domaine.

Aucune logique d'I/O ici : ce module ne décrit que des données et leurs
invariants, ce qui le rend trivial à tester et à réutiliser.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Iterator, Mapping

from apk_stats.exceptions import ConfigError

# Libellé de la ligne agrégée « tous pays confondus » dans la sortie.
WORLD_LABEL = "Tous les pays"

_PERIOD_RE = re.compile(r"^(\d{4})-(\d{2})$")

# Borne de date acceptée : `AAAA`, `AAAA-MM` ou `AAAA-MM-DD`.
_DATE_BOUND_RE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")


@dataclass(frozen=True, order=True)
class Period:
    """Mois calendaire (objet-valeur), ex. 2026-01.

    Immutable et ordonnable, ce qui permet un tri chronologique naturel.
    """

    year: int
    month: int

    def __post_init__(self) -> None:
        if not 1 <= self.month <= 12:
            raise ConfigError(f"Mois invalide : {self.month:02d} (attendu 01-12).")

    @classmethod
    def parse(cls, value: str) -> "Period":
        """Construit une période depuis une chaîne `AAAA-MM`."""
        match = _PERIOD_RE.match(value.strip())
        if not match:
            raise ConfigError(
                f"Période invalide : {value!r}. Format attendu 'AAAA-MM'."
            )
        return cls(year=int(match.group(1)), month=int(match.group(2)))

    @classmethod
    def range(cls, start: "Period", end: "Period") -> list["Period"]:
        """Liste des périodes mensuelles de `start` à `end` (bornes incluses)."""
        if end < start:
            raise ConfigError(
                f"La période de fin ({end}) précède celle de début ({start})."
            )
        return list(start._iter_until(end))

    def _iter_until(self, end: "Period") -> Iterator["Period"]:
        current = self
        while current <= end:
            yield current
            current = current.next()

    @classmethod
    def from_date(cls, value: date) -> "Period":
        """Période contenant la date donnée."""
        return cls(year=value.year, month=value.month)

    @property
    def first_day(self) -> date:
        return date(self.year, self.month, 1)

    @property
    def last_day(self) -> date:
        return date(self.year, self.month, calendar.monthrange(self.year, self.month)[1])

    def next(self) -> "Period":
        """Période du mois suivant."""
        if self.month == 12:
            return Period(self.year + 1, 1)
        return Period(self.year, self.month + 1)

    @property
    def yyyymm(self) -> str:
        """Représentation compacte `AAAAMM` (utilisée dans les noms de blob)."""
        return f"{self.year:04d}{self.month:02d}"

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


@dataclass(frozen=True)
class DateRange:
    """Intervalle de dates à extraire (objet-valeur, bornes incluses)."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ConfigError(
                f"La date de fin ({self.end}) précède celle de début ({self.start})."
            )

    @classmethod
    def parse(cls, start: str, end: str) -> "DateRange":
        """Construit l'intervalle depuis deux bornes `AAAA`, `AAAA-MM` ou `AAAA-MM-DD`.

        Une borne partielle est étendue : au premier jour de l'année ou du mois
        pour le début, au dernier jour pour la fin.
        """
        return cls(start=_parse_date_bound(start, end=False), end=_parse_date_bound(end, end=True))

    @property
    def periods(self) -> list[Period]:
        """Mois touchés par l'intervalle, dans l'ordre chronologique."""
        return Period.range(Period.from_date(self.start), Period.from_date(self.end))

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end

    def covers(self, period: Period) -> bool:
        """Vrai si le mois entier est inclus dans l'intervalle."""
        return self.start <= period.first_day and period.last_day <= self.end

    def __str__(self) -> str:
        return f"{self.start.isoformat()} → {self.end.isoformat()}"


def _parse_date_bound(value: str, *, end: bool) -> date:
    match = _DATE_BOUND_RE.match(value.strip())
    if not match:
        raise ConfigError(
            f"Date invalide : {value!r}. "
            f"Formats acceptés : 'AAAA', 'AAAA-MM' ou 'AAAA-MM-DD'."
        )
    year, month, day = match.groups()
    try:
        if month is None:
            return date(int(year), 12, 31) if end else date(int(year), 1, 1)
        period = Period(int(year), int(month))
        if day is None:
            return period.last_day if end else period.first_day
        return date(int(year), int(month), int(day))
    except ValueError as exc:
        raise ConfigError(f"Date invalide : {value!r}.") from exc


class Frequency(Enum):
    """Granularité temporelle des résultats produits."""

    YEARLY = "yearly"
    MONTHLY = "monthly"
    DAILY = "daily"

    @classmethod
    def parse(cls, value: str) -> "Frequency":
        """Construit la fréquence depuis sa valeur, sans tenir compte de la casse."""
        try:
            return cls(value.strip().lower())
        except ValueError:
            raise ConfigError(
                f"Fréquence invalide : {value!r}. "
                f"Valeurs acceptées : yearly, monthly, daily."
            ) from None

    @property
    def header(self) -> str:
        """Intitulé de la colonne temporelle dans le rapport de sortie."""
        return {
            Frequency.YEARLY: "Année",
            Frequency.MONTHLY: "Mois",
            Frequency.DAILY: "Jour",
        }[self]


@dataclass(frozen=True)
class CountryInstall:
    """Nombre d'installations pour un pays, à une date donnée si connue."""

    country_code: str
    installs: int
    day: date | None = None


@dataclass(frozen=True)
class StatsResult:
    """Résultat agrégé pour un package sur une période donnée.

    ``bucket`` identifie la période selon la fréquence : ``AAAA`` (yearly),
    ``AAAA-MM`` (monthly) ou ``AAAA-MM-DD`` (daily). Le format ISO
    garantit qu'un tri alphabétique est aussi chronologique.

    ``by_country`` associe chaque code pays ciblé à son total d'installations
    (ordre = ordre de la liste configurée). ``world`` est le total tous pays
    confondus présents dans le rapport.
    """

    package: str
    bucket: str
    by_country: Mapping[str, int] = field(default_factory=dict)
    world: int = 0
