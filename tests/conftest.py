"""Fixtures partagées."""

from __future__ import annotations

import pytest

from apk_stats.aggregator import Aggregator
from apk_stats.parsing import ReportParser


@pytest.fixture
def parser() -> ReportParser:
    return ReportParser()


@pytest.fixture
def aggregator() -> Aggregator:
    return Aggregator(("BF", "CI"))
