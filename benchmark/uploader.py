from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import urlparse

import requests


SUMMARY_FILENAMES = ("summary_overall.json", "summary_by_model.csv")


def _summary_files(metrics_dir: Path) -> list[Path]:
    return [metrics_dir / filename for filename in SUMMARY_FILENAMES if (metrics_dir / filename).exists()]


def _upload_file_target(experiment_name: str, metrics_dir: Path, target: str) -> None:
    destination_root = Path(target.removeprefix("file://"))
    destination_dir = destination_root / experiment_name
    destination_dir.mkdir(parents=True, exist_ok=True)
    for source in _summary_files(metrics_dir):
        shutil.copy2(source, destination_dir / source.name)


def _upload_s3_target(experiment_name: str, metrics_dir: Path, target: str) -> None:
    parsed = urlparse(target)
    bucket = parsed.netloc
    prefix = parsed.path.lstrip("/")
    if not bucket:
        raise ValueError(f"Invalid s3 target: {target}")

    import boto3  # Lazy import so non-S3 workflows do not require boto3.

    client = boto3.client("s3")
    for source in _summary_files(metrics_dir):
        key_parts = [part for part in (prefix, experiment_name, source.name) if part]
        key = "/".join(key_parts)
        client.upload_file(str(source), bucket, key)


def _upload_https_target(experiment_name: str, metrics_dir: Path, target: str) -> None:
    target_url = f"{target.rstrip('/')}/{experiment_name}/"
    files: dict[str, tuple[str, bytes, str]] = {}
    for source in _summary_files(metrics_dir):
        content_type = "application/json" if source.suffix == ".json" else "text/csv"
        files[source.name] = (source.name, source.read_bytes(), content_type)
    response = requests.post(target_url, files=files, timeout=30)
    response.raise_for_status()


def upload(experiment_name: str, metrics_dir: str | Path, target: str) -> None:
    metrics_dir = Path(metrics_dir)

    if target.startswith("file://"):
        _upload_file_target(experiment_name, metrics_dir, target)
        return
    if target.startswith("s3://"):
        _upload_s3_target(experiment_name, metrics_dir, target)
        return
    if target.startswith("https://"):
        _upload_https_target(experiment_name, metrics_dir, target)
        return

    raise NotImplementedError(f"Unsupported upload target: {target}")

