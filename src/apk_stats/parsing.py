"""Analyse des rapports d'installation par pays exportés par Play Console.

Les rapports sont des CSV encodés en UTF-16 dont les en-têtes varient selon la
langue du compte (anglais ou français). Cette couche isole tout le décodage et
la détection de colonnes, indépendamment de la provenance des octets.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass

from apk_stats.exceptions import ParsingError
from apk_stats.models import CountryInstall

logger = logging.getLogger(__name__)

# Fragments d'en-tête reconnus, en minuscules (anglais et français).
_COUNTRY_HINTS = ("countr", "pays")
_INSTALL_HINTS = (
    "daily device installs",
    "installations quotidiennes",
    "installs",
)

# Index de repli si l'en-tête n'est pas reconnu (format historique Play Console).
_DEFAULT_COUNTRY_IDX = 2
_DEFAULT_INSTALLS_IDX = 3


@dataclass(frozen=True)
class ColumnLayout:
    """Position des colonnes utiles dans le rapport."""

    country_idx: int
    installs_idx: int

    @property
    def min_width(self) -> int:
        return max(self.country_idx, self.installs_idx)


class ReportParser:
    """Transforme le contenu brut d'un rapport en enregistrements typés."""

    def parse(self, content: bytes) -> list[CountryInstall]:
        """Décode et analyse un rapport, ligne de données par ligne.

        Lève :class:`ParsingError` si les octets sont indécodables.
        """
        rows = self._read_rows(content)
        if not rows:
            return []

        layout = self._detect_columns(rows[0])
        records: list[CountryInstall] = []
        for row in rows[1:]:
            record = self._parse_row(row, layout)
            if record is not None:
                records.append(record)
        return records

    @staticmethod
    def _read_rows(content: bytes) -> list[list[str]]:
        try:
            text = content.decode("utf-16")
        except UnicodeDecodeError:
            try:
                text = content.decode("utf-16-le")
            except UnicodeDecodeError as exc:
                raise ParsingError("Impossible de décoder le rapport (UTF-16).") from exc
        return list(csv.reader(text.splitlines()))

    @staticmethod
    def _detect_columns(header_row: list[str]) -> ColumnLayout:
        header = [col.lower() for col in header_row]
        country_idx = _find_column(header, _COUNTRY_HINTS, _DEFAULT_COUNTRY_IDX)
        installs_idx = _find_column(header, _INSTALL_HINTS, _DEFAULT_INSTALLS_IDX)
        return ColumnLayout(country_idx=country_idx, installs_idx=installs_idx)

    @staticmethod
    def _parse_row(row: list[str], layout: ColumnLayout) -> CountryInstall | None:
        if not row or len(row) <= layout.min_width:
            return None
        country_code = row[layout.country_idx].strip().upper()
        try:
            installs = int(row[layout.installs_idx])
        except ValueError:
            installs = 0
        return CountryInstall(country_code=country_code, installs=installs)


def _find_column(header: list[str], hints: tuple[str, ...], default: int) -> int:
    """Renvoie l'index de la première colonne dont l'en-tête matche un indice."""
    for idx, col in enumerate(header):
        if any(hint in col for hint in hints):
            return idx
    logger.debug("En-tête non reconnu, repli sur l'index %d.", default)
    return default
