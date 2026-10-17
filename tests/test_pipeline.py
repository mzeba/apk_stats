"""Test d'intégration du pipeline (sans réseau, via doublures)."""

from __future__ import annotations

from apk_stats.aggregator import Aggregator
from apk_stats.models import DateRange, Frequency
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

    results = pipeline.run(["com.incubuo.mbem"], DateRange.parse("2026-01", "2026-01"))

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

    results = pipeline.run(["com.x"], DateRange.parse("2026-01", "2026-01"))

    assert results[0].by_country == {"BF": 100, "CI": 30}
    assert results[0].world == 135


def test_missing_reports_are_skipped():
    source = FakeStatsSource({("com.x", "202601"): _report(("BF", 10), ("FR", 5))})
    writer = InMemoryWriter()
    pipeline = _pipeline(source, writer)

    results = pipeline.run(["com.x"], DateRange.parse("2026-01", "2026-02"))

    # Seul janvier existe ; février est absent et ignoré silencieusement.
    assert [r.bucket for r in results] == ["2026-01"]


def test_no_data_writes_nothing():
    source = FakeStatsSource({})
    writer = InMemoryWriter()
    pipeline = _pipeline(source, writer)

    results = pipeline.run(["com.x"], DateRange.parse("2026-01", "2026-01"))

    assert results == []
    assert writer.results == []  # write() non appelé → reste vide


def _daily_report(*rows: tuple[str, str, int]) -> bytes:
    return utf16_report(
        [HEADER] + [[day, "com.x", code, str(n)] for day, code, n in rows]
    )


def test_partial_month_keeps_only_days_in_range():
    source = FakeStatsSource(
        {
            ("com.x", "202601"): _daily_report(
                ("2026-01-09", "BF", 1), ("2026-01-10", "BF", 10), ("2026-01-31", "FR", 5)
            ),
            ("com.x", "202602"): _daily_report(
                ("2026-02-05", "BF", 20), ("2026-02-06", "BF", 100)
            ),
        }
    )
    writer = InMemoryWriter()
    pipeline = _pipeline(source, writer)

    results = pipeline.run(["com.x"], DateRange.parse("2026-01-10", "2026-02-05"))

    assert [(r.bucket, r.by_country["BF"], r.world) for r in results] == [
        ("2026-01", 10, 15),
        ("2026-02", 20, 20),
    ]


def test_year_bound_fetches_every_month():
    source = FakeStatsSource({})
    pipeline = _pipeline(source, InMemoryWriter())

    pipeline.run(["com.x"], DateRange.parse("2025", "2025"))

    assert [yyyymm for _, yyyymm in source.calls] == [f"2025{m:02d}" for m in range(1, 13)]


def test_full_month_ignores_dates():
    # Un mois entièrement couvert n'est pas filtré : les lignes sans date comptent.
    source = FakeStatsSource(
        {("com.x", "202601"): _daily_report(("", "BF", 4), ("2026-01-02", "BF", 1))}
    )
    pipeline = _pipeline(source, InMemoryWriter())

    results = pipeline.run(["com.x"], DateRange.parse("2026-01", "2026-01"))

    assert results[0].by_country["BF"] == 5


def test_partial_month_drops_undated_rows():
    source = FakeStatsSource(
        {("com.x", "202601"): _daily_report(("", "BF", 4), ("2026-01-02", "BF", 1))}
    )
    pipeline = _pipeline(source, InMemoryWriter())

    results = pipeline.run(["com.x"], DateRange.parse("2026-01-01", "2026-01-15"))

    assert results[0].by_country["BF"] == 1


def test_yearly_frequency_sums_months_of_each_year():
    source = FakeStatsSource(
        {
            ("com.x", "202511"): _daily_report(("2025-11-03", "BF", 1)),
            ("com.x", "202512"): _daily_report(("2025-12-03", "BF", 2), ("2025-12-04", "FR", 4)),
            ("com.x", "202601"): _daily_report(("2026-01-03", "BF", 8)),
        }
    )
    pipeline = _pipeline(source, InMemoryWriter())

    results = pipeline.run(
        ["com.x"], DateRange.parse("2025-11", "2026-01"), Frequency.YEARLY
    )

    assert [(r.bucket, r.by_country["BF"], r.world) for r in results] == [
        ("2025", 3, 7),
        ("2026", 8, 8),
    ]


def test_daily_frequency_splits_by_day():
    source = FakeStatsSource(
        {
            ("com.x", "202601"): _daily_report(
                ("2026-01-01", "BF", 1),
                ("2026-01-01", "FR", 2),
                ("2026-01-02", "BF", 5),
                ("", "BF", 100),
            ),
        }
    )
    pipeline = _pipeline(source, InMemoryWriter())

    results = pipeline.run(["com.x"], DateRange.parse("2026-01", "2026-01"), Frequency.DAILY)

    assert [(r.bucket, r.by_country["BF"], r.world) for r in results] == [
        ("2026-01-01", 1, 3),
        ("2026-01-02", 5, 5),
    ]
