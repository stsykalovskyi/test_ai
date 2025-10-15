"""Training orchestration for Ukrainian morphological models."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..config import TrainingConfig
from ..datasets.ukrainian_names import MorphologySample, load_samples
from ..models.inflector import InflectorModel


class TrainingPipeline:
    def __init__(self, config: TrainingConfig | None = None):
        self.config = config or TrainingConfig()
        self.model = InflectorModel()
        self.fitted = False

    def load_training_data(self) -> Iterable[MorphologySample]:
        return load_samples(self.config.train_path)

    def fit(self) -> None:
        samples = list(self.load_training_data())
        if not samples:
            raise ValueError("No training samples available.")
        self.model.fit(samples)
        self.fitted = True

    def save_checkpoint(self, path: Path | None = None) -> Path:
        if not self.fitted:
            raise RuntimeError("Model must be fitted before saving a checkpoint.")
        checkpoint_dir = path or self.config.checkpoints_dir
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        output = checkpoint_dir / "latest.json"
        self.model.save(output)
        return output
