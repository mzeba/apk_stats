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
from apk_stats.models import CountryInstall, DateRange, Frequency, Period, StatsResult
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

    def run(
        self,
        packages: Sequence[str],
        date_range: DateRange,
        frequency: Frequency = Frequency.MONTHLY,
    ) -> list[StatsResult]:
        """Extrait, agrège et écrit les résultats. Renvoie les résultats produits.

        Un résultat est produit par package et par année, mois ou jour selon
        ``frequency``. Seuls les jours compris dans ``date_range`` comptent.
        """
        results: list[StatsResult] = []
        logger.info("Intervalle analysé : %s (fréquence %s)", date_range, frequency.value)
        for package in packages:
            logger.info("Analyse de l'application : %s", package)
            buckets: dict[str, list[CountryInstall]] = {}
            for period in date_range.periods:
                records = self._extract(package, period, date_range)
                if records is None:
                    continue
                for bucket, rows in self._group(records, period, frequency, package).items():
                    buckets.setdefault(bucket, []).extend(rows)
            for bucket, rows in buckets.items():
                results.append(self._aggregate(package, bucket, rows))

        if results:
            self._writer.write(results)
        else:
            logger.warning(
                "Aucune donnée collectée. Vérifiez le bucket, les droits "
                "ou la période demandée."
            )
        return results

    def _extract(
        self, package: str, period: Period, date_range: DateRange
    ) -> list[CountryInstall] | None:
        """Lignes du rapport mensuel comprises dans l'intervalle, ou ``None`` si absent."""
        try:
            content = self._source.fetch(package, period)
        except SourceError as exc:
            logger.error("%s / %s : %s", package, period, exc)
            return None

        if content is None:
            return None

        records = self._parser.parse(content)
        if not date_range.covers(period):
            records = self._keep_in_range(records, date_range, package, period)
        return records

    @staticmethod
    def _group(
        records: list[CountryInstall],
        period: Period,
        frequency: Frequency,
        package: str,
    ) -> dict[str, list[CountryInstall]]:
        """Répartit les lignes d'un mois par année, mois ou jour."""
        if frequency is Frequency.YEARLY:
            return {f"{period.year:04d}": records}
        if frequency is Frequency.MONTHLY:
            return {str(period): records}

        by_day: dict[str, list[CountryInstall]] = {}
        undated = 0
        for record in records:
            if record.day is None:
                undated += 1
                continue
            by_day.setdefault(record.day.isoformat(), []).append(record)
        if undated:
            logger.warning(
                "%s / %s : %d ligne(s) sans date exploitable ignorée(s) "
                "(fréquence daily).",
                package,
                period,
                undated,
            )
        return by_day

    def _aggregate(
        self, package: str, bucket: str, records: list[CountryInstall]
    ) -> StatsResult:
        result = self._aggregator.aggregate(package, bucket, records)
        by_country = ", ".join(
            f"{code}={count}" for code, count in result.by_country.items()
        )
        logger.info(
            "%s / %s : %s, Monde=%d",
            package,
            bucket,
            by_country,
            result.world,
        )
        return result

    @staticmethod
    def _keep_in_range(
        records: list[CountryInstall],
        date_range: DateRange,
        package: str,
        period: Period,
    ) -> list[CountryInstall]:
        """Ne garde que les lignes datées comprises dans l'intervalle."""
        undated = sum(1 for r in records if r.day is None)
        if undated:
            logger.warning(
                "%s / %s : %d ligne(s) sans date exploitable ignorée(s) "
                "(mois couvert partiellement).",
                package,
                period,
                undated,
            )
        return [r for r in records if r.day is not None and date_range.contains(r.day)]
