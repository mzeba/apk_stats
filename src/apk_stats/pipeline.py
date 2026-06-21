"""Orchestrateur du pipeline ETL (pattern Facade).

Coordonne les étapes Extract → Transform → Load en s'appuyant uniquement sur
des abstractions injectées (source, parser, agrégateur, writer). Il ignore tout
de Google Cloud comme du format CSV : ces détails vivent dans leurs couches.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from apk_stats.aggregator import Aggregator
from apk_stats.exceptions import SourceError
from apk_stats.models import MonthlyResult, Period
from apk_stats.parsing import ReportParser
from apk_stats.sources.base import StatsSource
from apk_stats.writers.base import ReportWriter

logger = logging.getLogger(__name__)


class StatsPipeline:
    """Façade exposant l'exécution complète du traitement."""

    def __init__(
        self,
        source: StatsSource,
        writer: ReportWriter,
        aggregator: Aggregator,
        *,
        parser: ReportParser | None = None,
    ) -> None:
        self._source = source
        self._writer = writer
        self._aggregator = aggregator
        self._parser = parser or ReportParser()

    def run(self, packages: Sequence[str], periods: Sequence[Period]) -> list[MonthlyResult]:
        """Extrait, agrège et écrit les résultats. Renvoie les résultats produits."""
        results: list[MonthlyResult] = []
        for package in packages:
            logger.info("Analyse de l'application : %s", package)
            for period in periods:
                result = self._process(package, period)
                if result is not None:
                    results.append(result)

        if results:
            self._writer.write(results)
        else:
            logger.warning(
                "Aucune donnée collectée. Vérifiez le bucket, les droits "
                "ou la période demandée."
            )
        return results

    def _process(self, package: str, period: Period) -> MonthlyResult | None:
        try:
            content = self._source.fetch(package, period)
        except SourceError as exc:
            logger.error("%s / %s : %s", package, period, exc)
            return None

        if content is None:
            return None

        records = self._parser.parse(content)
        result = self._aggregator.aggregate(package, period, records)
        by_country = ", ".join(
            f"{code}={count}" for code, count in result.by_country.items()
        )
        logger.info(
            "%s / %s : %s, Monde=%d",
            package,
            period,
            by_country,
            result.world,
        )
        return result
