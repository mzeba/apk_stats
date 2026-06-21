"""Logique métier d'agrégation géographique.

Sépare le « quoi » (totaux par pays ciblé et total monde) du « comment »
(source des données, format de sortie).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from apk_stats.exceptions import ConfigError
from apk_stats.models import CountryInstall, MonthlyResult, Period


class Aggregator:
    """Agrège des installations par pays en totaux par pays ciblé + total monde.

    La liste des pays ciblés est injectée à la construction : la logique métier
    ne connaît aucun pays « en dur ».
    """

    def __init__(self, target_countries: Sequence[str]) -> None:
        normalized = tuple(dict.fromkeys(c.strip().upper() for c in target_countries))
        if not normalized:
            raise ConfigError("Au moins un pays cible doit être fourni.")
        self._target_countries = normalized

    @property
    def target_countries(self) -> tuple[str, ...]:
        return self._target_countries

    def aggregate(
        self,
        package: str,
        period: Period,
        records: Iterable[CountryInstall],
    ) -> MonthlyResult:
        """Calcule le total par pays ciblé et le total monde pour un package/période."""
        by_country: dict[str, int] = {code: 0 for code in self._target_countries}
        world = 0
        for record in records:
            world += record.installs
            code = record.country_code.strip().upper()
            if code in by_country:
                by_country[code] += record.installs
        return MonthlyResult(
            package=package,
            period=period,
            by_country=by_country,
            world=world,
        )
