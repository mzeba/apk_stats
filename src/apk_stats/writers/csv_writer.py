"""Écriture du rapport consolidé au format CSV."""

from __future__ import annotations

import csv
import logging
from collections.abc import Sequence

from apk_stats.exceptions import EdmStatsError
from apk_stats.models import WORLD_LABEL, MonthlyResult
from apk_stats.writers.base import ReportWriter

logger = logging.getLogger(__name__)

HEADER = ["Application", "Mois", "Zone Géographique", "Nombre de Téléchargements"]


class CsvReportWriter(ReportWriter):
    """Sérialise les résultats en CSV : une ligne par pays ciblé, puis le total monde."""

    def __init__(self, output_path: str) -> None:
        self._output_path = output_path

    def write(self, results: Sequence[MonthlyResult]) -> None:
        ordered = sorted(results, key=lambda r: (r.package, r.period))
        rows_written = 0
        try:
            with open(self._output_path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(HEADER)
                for result in ordered:
                    for zone, value in self._zones(result):
                        writer.writerow(
                            [result.package, str(result.period), zone, value]
                        )
                        rows_written += 1
        except OSError as exc:
            raise EdmStatsError(
                f"Erreur d'écriture du fichier '{self._output_path}'."
            ) from exc
        logger.info("Rapport écrit : %s (%d lignes)", self._output_path, rows_written)

    @staticmethod
    def _zones(result: MonthlyResult) -> list[tuple[str, int]]:
        """Lignes (zone, valeur) : un pays ciblé par ligne, puis le total monde."""
        zones: list[tuple[str, int]] = list(result.by_country.items())
        zones.append((WORLD_LABEL, result.world))
        return zones
