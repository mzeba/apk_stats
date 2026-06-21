"""Tests de la source GCS : construction du chemin et garde-fous de sécurité."""

from __future__ import annotations

import pytest

from apk_stats.exceptions import SourceError
from apk_stats.models import Period
from apk_stats.sources.gcs import GcsStatsSource


class _FakeBlob:
    def __init__(self, data: bytes | None) -> None:
        self._data = data

    def exists(self) -> bool:
        return self._data is not None

    def download_as_bytes(self) -> bytes:
        assert self._data is not None
        return self._data


class _FakeBucket:
    def __init__(self, blobs: dict[str, bytes]) -> None:
        self._blobs = blobs
        self.requested: list[str] = []

    def blob(self, name: str) -> _FakeBlob:
        self.requested.append(name)
        return _FakeBlob(self._blobs.get(name))


class _FakeClient:
    def __init__(self, bucket: _FakeBucket) -> None:
        self._bucket = bucket

    def bucket(self, name: str) -> _FakeBucket:
        return self._bucket


def test_builds_expected_blob_path():
    bucket = _FakeBucket(
        {"stats/installs/installs_com.incubuo.mbem_202601_country.csv": b"data"}
    )
    source = GcsStatsSource(_FakeClient(bucket), "my-bucket")

    content = source.fetch("com.incubuo.mbem", Period.parse("2026-01"))

    assert content == b"data"
    assert bucket.requested == [
        "stats/installs/installs_com.incubuo.mbem_202601_country.csv"
    ]


def test_missing_blob_returns_none():
    bucket = _FakeBucket({})
    source = GcsStatsSource(_FakeClient(bucket), "my-bucket")
    assert source.fetch("com.x.y", Period.parse("2026-01")) is None


@pytest.mark.parametrize("package", ["../evil", "com/x", "a b", "x;rm -rf"])
def test_rejects_unsafe_package_names(package):
    bucket = _FakeBucket({})
    source = GcsStatsSource(_FakeClient(bucket), "my-bucket")
    with pytest.raises(SourceError):
        source.fetch(package, Period.parse("2026-01"))


def test_download_failure_is_wrapped():
    class _BoomBucket(_FakeBucket):
        def blob(self, name: str):
            raise RuntimeError("network down")

    source = GcsStatsSource(_FakeClient(_BoomBucket({})), "my-bucket")
    with pytest.raises(SourceError):
        source.fetch("com.x.y", Period.parse("2026-01"))
