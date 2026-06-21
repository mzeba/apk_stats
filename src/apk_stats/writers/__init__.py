"""Sorties de rapports agrégés (abstraction Strategy)."""

from apk_stats.writers.base import ReportWriter
from apk_stats.writers.csv_writer import CsvReportWriter

__all__ = ["ReportWriter", "CsvReportWriter"]
