"""Objets-valeur immutables du domaine.

Aucune logique d'I/O ici : ce module ne décrit que des données et leurs
invariants, ce qui le rend trivial à tester et à réutiliser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator, Mapping

from apk_stats.exceptions import ConfigError

# Libellé de la ligne agrégée « tous pays confondus » dans la sortie.
WORLD_LABEL = "Tous les pays"

_PERIOD_RE = re.compile(r"^(\d{4})-(\d{2})$")


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
class CountryInstall:
    """Nombre d'installations cumulé pour un pays sur une période."""

    country_code: str
    installs: int


@dataclass(frozen=True)
class MonthlyResult:
    """Résultat agrégé pour un package sur une période donnée.

    ``by_country`` associe chaque code pays ciblé à son total d'installations
    (ordre = ordre de la liste configurée). ``world`` est le total tous pays
    confondus présents dans le rapport.
    """

    package: str
    period: Period
    by_country: Mapping[str, int] = field(default_factory=dict)
    world: int = 0
