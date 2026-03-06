from __future__ import annotations

import shutil
from pathlib import Path


def upload(experiment_name: str, metrics_dir: str | Path, target: str) -> None:
    metrics_dir = Path(metrics_dir)

    if target.startswith("file://"):
        destination_root = Path(target.removeprefix("file://"))
        destination_dir = destination_root / experiment_name
        destination_dir.mkdir(parents=True, exist_ok=True)

        for filename in ("summary_overall.json", "summary_by_model.csv"):
            source = metrics_dir / filename
            if source.exists():
                shutil.copy2(source, destination_dir / filename)
        return

    raise NotImplementedError(f"Unsupported upload target: {target}")

