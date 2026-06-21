"""Test d'intégration du pipeline (sans réseau, via doublures)."""

from __future__ import annotations

from apk_stats.aggregator import Aggregator
from apk_stats.models import Period
from apk_stats.pipeline import StatsPipeline
from tests.fakes import FakeStatsSource, InMemoryWriter, utf16_report

HEADER = ["Date", "Package Name", "Country", "Daily Device Installs"]


def _report(*country_installs: tuple[str, int]) -> bytes:
    rows = [HEADER]
    rows += [["2026-01-01", "com.x", code, str(n)] for code, n in country_installs]
    return utf16_report(rows)


def _pipeline(source: FakeStatsSource, writer: InMemoryWriter, countries=("BF",)) -> StatsPipeline:
    return StatsPipeline(source, writer, Aggregator(countries))


def test_pipeline_reproduces_reference_figures():
    # Chiffres connus de stats_mensuelles_burkina_vs_monde.csv (mbem, 2026-01).
    source = FakeStatsSource(
        {("com.incubuo.mbem", "202601"): _report(("BF", 563), ("FR", 48))}
    )
    writer = InMemoryWriter()
    pipeline = _pipeline(source, writer)

    results = pipeline.run(["com.incubuo.mbem"], [Period.parse("2026-01")])

    assert len(results) == 1
    assert results[0].by_country["BF"] == 563
    assert results[0].world == 611
    assert writer.results == results


def test_pipeline_breaks_down_multiple_countries():
    source = FakeStatsSource(
        {("com.x", "202601"): _report(("BF", 100), ("CI", 30), ("FR", 5))}
    )
    writer = InMemoryWriter()
    pipeline = _pipeline(source, writer, countries=("BF", "CI"))

    results = pipeline.run(["com.x"], [Period.parse("2026-01")])

    assert results[0].by_country == {"BF": 100, "CI": 30}
    assert results[0].world == 135


def test_missing_reports_are_skipped():
    source = FakeStatsSource({("com.x", "202601"): _report(("BF", 10), ("FR", 5))})
    writer = InMemoryWriter()
    pipeline = _pipeline(source, writer)

    periods = [Period.parse("2026-01"), Period.parse("2026-02")]
    results = pipeline.run(["com.x"], periods)

    # Seul janvier existe ; février est absent et ignoré silencieusement.
    assert [str(r.period) for r in results] == ["2026-01"]


def test_no_data_writes_nothing():
    source = FakeStatsSource({})
    writer = InMemoryWriter()
    pipeline = _pipeline(source, writer)

    results = pipeline.run(["com.x"], [Period.parse("2026-01")])

    assert results == []
    assert writer.results == []  # write() non appelé → reste vide
