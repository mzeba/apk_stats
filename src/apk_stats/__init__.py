"""Extraction et agrégation mensuelle des statistiques d'installation Play Store.

Pipeline ETL ventilant les installations par pays (liste configurable) et au
total monde, à partir du bucket Google Play Console.
"""

from apk_stats.config import AppConfig
from apk_stats.models import CountryInstall, MonthlyResult, Period
from apk_stats.pipeline import StatsPipeline

__version__ = "1.0.0"

__all__ = [
    "AppConfig",
    "CountryInstall",
    "MonthlyResult",
    "Period",
    "StatsPipeline",
]
