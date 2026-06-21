"""Source de données adossée à Google Cloud Storage (bucket Play Console)."""

from __future__ import annotations

import logging
import re
from typing import Protocol

from apk_stats.exceptions import SourceError
from apk_stats.models import Period
from apk_stats.sources.base import StatsSource

logger = logging.getLogger(__name__)

# Garde-fou : un package ne doit contenir que des caractères sûrs avant d'être
# interpolé dans le chemin d'un objet GCS (défense en profondeur contre
# l'injection de chemin, en complément de la validation faite dans config.py).
_SAFE_PACKAGE_RE = re.compile(r"^[A-Za-z0-9._]+$")


class _BlobLike(Protocol):
    def exists(self) -> bool: ...
    def download_as_bytes(self) -> bytes: ...


class _BucketLike(Protocol):
    def blob(self, name: str) -> _BlobLike: ...


class _ClientLike(Protocol):
    def bucket(self, name: str) -> _BucketLike: ...


class GcsStatsSource(StatsSource):
    """Récupère les rapports `installs_<package>_<AAAAMM>_country.csv` du bucket.

    Le client GCS est **injecté** : la classe ne crée aucune connexion elle-même,
    ce qui la rend testable et respecte l'inversion de dépendances.
    """

    _BLOB_TEMPLATE = "stats/installs/installs_{package}_{yyyymm}_country.csv"

    def __init__(self, client: _ClientLike, bucket_name: str) -> None:
        self._bucket = client.bucket(bucket_name)
        self._bucket_name = bucket_name

    def fetch(self, package: str, period: Period) -> bytes | None:
        blob_name = self._blob_name(package, period)
        try:
            blob = self._bucket.blob(blob_name)
            if not blob.exists():
                logger.info("Rapport non disponible : %s", blob_name)
                return None
            logger.debug("Téléchargement de %s", blob_name)
            return blob.download_as_bytes()
        except SourceError:
            raise
        except Exception as exc:  # erreurs réseau / SDK GCS
            raise SourceError(
                f"Échec d'accès au rapport '{blob_name}' "
                f"dans le bucket '{self._bucket_name}'."
            ) from exc

    @classmethod
    def _blob_name(cls, package: str, period: Period) -> str:
        if not _SAFE_PACKAGE_RE.match(package):
            raise SourceError(f"Nom de package non sûr : {package!r}.")
        # `period.yyyymm` est garanti numérique par construction de Period.
        return cls._BLOB_TEMPLATE.format(package=package, yyyymm=period.yyyymm)
