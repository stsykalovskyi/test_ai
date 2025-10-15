"""Training pipeline for person classification model."""

from __future__ import annotations

from pathlib import Path

import torch

from ..config import TrainingConfig
from ..datasets.person_images import load_person_samples
from ..models.person_classifier import PersonClassifierModel


class PersonClassificationPipeline:
    """Training pipeline for person detection model."""

    def __init__(self, config: TrainingConfig | None = None):
        self.config = config or TrainingConfig()
        self.config.experiment_name = "person-classifier"

        # Determine available device
        if self.config.accelerator == "cpu":
            device = "cpu"
        elif self.config.accelerator == "gpu":
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cpu":
                print("Warning: GPU requested but CUDA not available. Using CPU instead.")
        else:
            device = "cpu"

        self.model = PersonClassifierModel(device=device)
        self.fitted = False

    def load_training_data(self) -> list:
        """Load all training samples into memory."""
        # Override default path for person images
        dataset_path = self.config.train_path.parent / "person_images.csv"
        return list(load_person_samples(dataset_path))

    def fit(self) -> None:
        """Train the person classifier model."""
        samples = self.load_training_data()
        if not samples:
            raise ValueError("No training samples available.")

        self.model.fit(
            samples,
            epochs=self.config.max_epochs,
            learning_rate=self.config.learning_rate,
        )
        self.fitted = True

    def save_checkpoint(self, path: Path | None = None) -> Path:
        """Save model checkpoint."""
        if not self.fitted:
            raise RuntimeError("Model must be fitted before saving a checkpoint.")

        checkpoint_dir = path or self.config.checkpoints_dir
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        output = checkpoint_dir / "latest.pth"
        self.model.save(output)
        return output

    def evaluate(self, test_path: Path | None = None) -> dict:
        """Evaluate model on test set."""
        if not self.fitted:
            raise RuntimeError("Model must be fitted before evaluation.")

        test_samples = list(load_person_samples(test_path or self.config.test_path.parent / "person_images_test.csv"))
        if not test_samples:
            return {"accuracy": 0.0, "total": 0}

        correct = 0
        total = 0
        for sample in test_samples:
            try:
                image = sample.load_image()
                predicted_label, confidence = self.model.predict(image)
                if predicted_label == sample.label:
                    correct += 1
                total += 1
            except Exception:
                continue

        accuracy = correct / total if total > 0 else 0.0
        return {"accuracy": accuracy, "correct": correct, "total": total}
