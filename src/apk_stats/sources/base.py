"""Interface de source de données (pattern Repository / Strategy).

Le pipeline ne dépend que de cette abstraction : la source réelle (GCS) et les
sources de test (factices) sont interchangeables sans toucher au reste du code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from apk_stats.models import Period


class StatsSource(ABC):
    """Fournit le contenu brut d'un rapport pour un package et une période."""

    @abstractmethod
    def fetch(self, package: str, period: Period) -> bytes | None:
        """Renvoie les octets du rapport, ou ``None`` s'il n'existe pas.

        Lève :class:`edm_stats.exceptions.SourceError` en cas d'échec d'accès.
        """
        raise NotImplementedError
