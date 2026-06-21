"""Tests du parsing des rapports (UTF-16, en-têtes FR/EN, robustesse)."""

from __future__ import annotations

import pytest

from apk_stats.exceptions import ParsingError
from apk_stats.parsing import ReportParser
from tests.fakes import utf16_report

EN_HEADER = ["Date", "Package Name", "Country", "Daily Device Installs"]
FR_HEADER = ["Date", "Nom du package", "Pays", "Installations quotidiennes des appareils"]


def test_parses_english_header(parser: ReportParser):
    content = utf16_report([EN_HEADER, ["2026-01-01", "com.x", "BF", "10"]])
    records = parser.parse(content)
    assert [(r.country_code, r.installs) for r in records] == [("BF", 10)]


def test_parses_french_header(parser: ReportParser):
    content = utf16_report([FR_HEADER, ["2026-01-01", "com.x", "fr", "7"]])
    records = parser.parse(content)
    assert [(r.country_code, r.installs) for r in records] == [("FR", 7)]


def test_empty_report_yields_no_records(parser: ReportParser):
    assert parser.parse(utf16_report([])) == []


def test_header_only_yields_no_records(parser: ReportParser):
    assert parser.parse(utf16_report([EN_HEADER])) == []


def test_non_numeric_installs_count_as_zero(parser: ReportParser):
    content = utf16_report([EN_HEADER, ["2026-01-01", "com.x", "BF", "N/A"]])
    records = parser.parse(content)
    assert records[0].installs == 0


def test_short_rows_are_skipped(parser: ReportParser):
    content = utf16_report([EN_HEADER, ["incomplete"], ["2026-01-01", "com.x", "BF", "3"]])
    records = parser.parse(content)
    assert [(r.country_code, r.installs) for r in records] == [("BF", 3)]


def test_undecodable_content_raises(parser: ReportParser):
    with pytest.raises(ParsingError):
        parser.parse(b"\xff")
