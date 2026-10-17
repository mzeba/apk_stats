"""Interface de sortie de rapport (pattern Strategy).

Ajouter un format (JSON, base SQL, tableur...) revient à fournir une nouvelle
implémentation, sans modifier le pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from apk_stats.models import StatsResult


class ReportWriter(ABC):
    """Persiste une liste de résultats agrégés."""

    @abstractmethod
    def write(self, results: Sequence[StatsResult]) -> None:
        raise NotImplementedError
