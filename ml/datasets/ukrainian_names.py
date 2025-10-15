"""Utilities for working with Ukrainian name/title corpora."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from test_ai.settings import DATA_DIR


@dataclass
class MorphologySample:
    lemma: str
    target_case: str
    inflected: str
    gender: str | None = None
    animacy: str | None = None
    title: str | None = None


def load_samples(path: Path | None = None) -> Iterator[MorphologySample]:
    """Stream samples from a CSV file for memory-efficient training."""

    dataset_path = path or DATA_DIR / "processed" / "train.csv"
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")

    with dataset_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield MorphologySample(
                lemma=row["lemma"],
                target_case=row["target_case"],
                inflected=row["inflected"],
                gender=row.get("gender") or None,
                animacy=row.get("animacy") or None,
                title=row.get("title") or None,
            )


def save_samples(path: Path, rows: Iterable[MorphologySample]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["lemma", "target_case", "inflected", "gender", "animacy", "title"])
        for sample in rows:
            writer.writerow([
                sample.lemma,
                sample.target_case,
                sample.inflected,
                sample.gender or "",
                sample.animacy or "",
                sample.title or "",
            ])
