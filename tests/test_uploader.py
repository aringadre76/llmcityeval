from __future__ import annotations

import sys
from pathlib import Path

import pytest

from benchmark.uploader import upload


def test_upload_supports_https_target(tmp_path: Path, monkeypatch) -> None:
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    (metrics_dir / "summary_overall.json").write_text('{"ok": true}', encoding="utf-8")
    (metrics_dir / "summary_by_model.csv").write_text("model\nbaseline\n", encoding="utf-8")

    posted: list[tuple[str, list[str]]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

    def fake_post(url, files, timeout):  # noqa: ANN001
        _ = timeout
        posted.append((url, sorted(files.keys())))
        return FakeResponse()

    monkeypatch.setattr("benchmark.uploader.requests.post", fake_post)

    upload("citybench_v1", metrics_dir, "https://example.com/upload")

    assert posted == [("https://example.com/upload/citybench_v1/", ["summary_by_model.csv", "summary_overall.json"])]


def test_upload_supports_s3_target(tmp_path: Path, monkeypatch) -> None:
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    overall = metrics_dir / "summary_overall.json"
    by_model = metrics_dir / "summary_by_model.csv"
    overall.write_text('{"ok": true}', encoding="utf-8")
    by_model.write_text("model\nbaseline\n", encoding="utf-8")

    uploads: list[tuple[str, str, str]] = []

    class FakeS3Client:
        def upload_file(self, source, bucket, key):  # noqa: ANN001
            uploads.append((source, bucket, key))

    class FakeBoto3Module:
        @staticmethod
        def client(name: str) -> FakeS3Client:
            assert name == "s3"
            return FakeS3Client()

    monkeypatch.setitem(sys.modules, "boto3", FakeBoto3Module())

    upload("citybench_v1", metrics_dir, "s3://my-bucket/citybench")

    assert (str(overall), "my-bucket", "citybench/citybench_v1/summary_overall.json") in uploads
    assert (str(by_model), "my-bucket", "citybench/citybench_v1/summary_by_model.csv") in uploads


def test_upload_rejects_invalid_s3_target(tmp_path: Path) -> None:
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    with pytest.raises(ValueError):
        upload("citybench_v1", metrics_dir, "s3://")
