"""Utilities for loading person classification image datasets."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

from PIL import Image

from test_ai.settings import DATA_DIR


PersonLabel = Literal["man", "woman", "nobody"]


@dataclass
class PersonImageSample:
    """Single training sample for person classification."""

    image_path: Path
    label: PersonLabel

    def load_image(self) -> Image.Image:
        """Load and return the PIL Image."""
        return Image.open(self.image_path).convert("RGB")


def load_person_samples(path: Path | None = None) -> Iterator[PersonImageSample]:
    """Stream person classification samples from a CSV file.

    Expected CSV format:
    - image_path: relative path to image file from DATA_DIR
    - label: one of 'man', 'woman', 'nobody'

    Example:
        image_path,label
        processed/person_images/img_001.jpg,man
        processed/person_images/img_002.jpg,woman
        processed/person_images/img_003.jpg,nobody
    """
    dataset_path = path or DATA_DIR / "processed" / "person_images.csv"
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")

    with dataset_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            image_path = DATA_DIR / row["image_path"]
            if not image_path.exists():
                continue  # Skip missing images

            label = row["label"].lower().strip()
            if label not in ("man", "woman", "nobody"):
                continue  # Skip invalid labels

            yield PersonImageSample(
                image_path=image_path,
                label=label,  # type: ignore
            )


def save_person_samples(path: Path, samples: list[PersonImageSample]) -> None:
    """Save person classification samples to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["image_path", "label"])
        for sample in samples:
            # Store relative path from DATA_DIR
            try:
                relative_path = sample.image_path.relative_to(DATA_DIR)
            except ValueError:
                relative_path = sample.image_path
            writer.writerow([str(relative_path), sample.label])
