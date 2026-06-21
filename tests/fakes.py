"""Doublures de test : source factice et writer en mémoire.

Permettent d'exercer le pipeline de bout en bout sans réseau ni système de
fichiers, en respectant les interfaces StatsSource / ReportWriter.
"""

from __future__ import annotations

from collections.abc import Sequence

from apk_stats.models import MonthlyResult, Period
from apk_stats.sources.base import StatsSource
from apk_stats.writers.base import ReportWriter


def utf16_report(rows: list[list[str]]) -> bytes:
    """Encode des lignes en CSV UTF-16, comme le ferait Play Console."""
    lines = [",".join(cells) for cells in rows]
    return "\r\n".join(lines).encode("utf-16")


class FakeStatsSource(StatsSource):
    """Renvoie des octets pré-enregistrés, indexés par (package, période)."""

    def __init__(self, reports: dict[tuple[str, str], bytes]) -> None:
        self._reports = reports
        self.calls: list[tuple[str, str]] = []

    def fetch(self, package: str, period: Period) -> bytes | None:
        key = (package, period.yyyymm)
        self.calls.append(key)
        return self._reports.get(key)


class InMemoryWriter(ReportWriter):
    """Capture les résultats au lieu de les persister."""

    def __init__(self) -> None:
        self.results: list[MonthlyResult] = []

    def write(self, results: Sequence[MonthlyResult]) -> None:
        self.results = list(results)
