"""Person classification model using pre-trained CNN."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

from ..datasets.person_images import PersonImageSample, PersonLabel


LABEL_TO_IDX = {"man": 0, "woman": 1, "nobody": 2}
IDX_TO_LABEL = {0: "man", 1: "woman", 2: "nobody"}


@dataclass
class PersonClassifierCheckpoint:
    """Checkpoint for person classifier model."""

    state_dict: dict[str, Any]
    metadata: dict[str, Any]

    def save(self, path: Path) -> None:
        """Save checkpoint to disk."""
        torch.save({
            "state_dict": self.state_dict,
            "metadata": self.metadata,
        }, path)

    @classmethod
    def load(cls, path: Path) -> PersonClassifierCheckpoint:
        """Load checkpoint from disk."""
        checkpoint = torch.load(path, map_location="cpu")
        return cls(
            state_dict=checkpoint["state_dict"],
            metadata=checkpoint.get("metadata", {}),
        )


class PersonClassifier(nn.Module):
    """CNN-based classifier for person detection (man/woman/nobody).

    Uses MobileNetV2 as backbone for efficient inference.
    """

    def __init__(self, pretrained: bool = True):
        super().__init__()
        # Use MobileNetV2 as feature extractor
        self.backbone = models.mobilenet_v2(pretrained=pretrained)
        # Replace classifier head for 3 classes
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(in_features, 3),
        )

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)

    def preprocess_image(self, image: Image.Image) -> torch.Tensor:
        """Convert PIL image to model input tensor."""
        return self.transform(image).unsqueeze(0)

    def predict(self, image: Image.Image) -> tuple[PersonLabel, float]:
        """Predict person type from image.

        Returns:
            Tuple of (predicted_label, confidence)
        """
        self.eval()
        with torch.no_grad():
            tensor = self.preprocess_image(image)
            logits = self.forward(tensor)
            probs = torch.softmax(logits, dim=1)
            confidence, predicted_idx = torch.max(probs, dim=1)

            label = IDX_TO_LABEL[predicted_idx.item()]
            return label, confidence.item()  # type: ignore


@dataclass
class PersonClassifierModel:
    """Wrapper for training and using the person classifier."""

    model: PersonClassifier = field(default_factory=lambda: PersonClassifier(pretrained=True))
    metadata: dict[str, Any] = field(default_factory=dict)
    device: str = "cpu"

    def __post_init__(self):
        self.model = self.model.to(self.device)

    def fit(self, samples: list[PersonImageSample], epochs: int = 5, learning_rate: float = 1e-4) -> None:
        """Train the model on provided samples.

        For a more robust implementation, this should use DataLoader and proper training loop.
        This is a simplified version.
        """
        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        criterion = nn.CrossEntropyLoss()

        # Track sample counts per class
        class_counts = {"man": 0, "woman": 0, "nobody": 0}
        valid_samples = []

        # Pre-validate all samples
        for sample in samples:
            try:
                image = sample.load_image()
                valid_samples.append(sample)
                class_counts[sample.label] += 1
            except Exception as e:
                print(f"Warning: Skipping invalid image {sample.image_path}: {e}")
                continue

        self.metadata["class_distribution"] = class_counts
        print(f"Training on {len(valid_samples)} samples: {class_counts}")

        for epoch in range(epochs):
            total_loss = 0.0
            correct = 0
            total = 0

            for sample in valid_samples:
                try:
                    image = sample.load_image()
                    tensor = self.model.preprocess_image(image).to(self.device)
                    label_idx = LABEL_TO_IDX[sample.label]
                    target = torch.tensor([label_idx], device=self.device)

                    optimizer.zero_grad()
                    output = self.model(tensor)
                    loss = criterion(output, target)
                    loss.backward()
                    optimizer.step()

                    total_loss += loss.item()

                    # Calculate accuracy
                    _, predicted = torch.max(output, 1)
                    total += 1
                    correct += (predicted == target).sum().item()

                except Exception as e:
                    print(f"Error processing {sample.image_path}: {e}")
                    continue

            avg_loss = total_loss / max(len(valid_samples), 1)
            accuracy = correct / total if total > 0 else 0
            self.metadata[f"epoch_{epoch + 1}_loss"] = avg_loss
            self.metadata[f"epoch_{epoch + 1}_accuracy"] = accuracy
            print(f"Epoch {epoch + 1}/{epochs} - Loss: {avg_loss:.4f}, Accuracy: {accuracy:.4f}")

        self.metadata["epochs"] = epochs
        self.metadata["samples"] = len(valid_samples)

    def predict(self, image: Image.Image) -> tuple[PersonLabel, float]:
        """Predict person type from image."""
        return self.model.predict(image)

    def save(self, path: Path) -> Path:
        """Save model checkpoint."""
        checkpoint = PersonClassifierCheckpoint(
            state_dict=self.model.state_dict(),
            metadata=self.metadata,
        )
        checkpoint.save(path)
        return path

    @classmethod
    def load(cls, path: Path, device: str = "cpu") -> PersonClassifierModel:
        """Load model from checkpoint."""
        checkpoint = PersonClassifierCheckpoint.load(path)
        model = PersonClassifier(pretrained=False)
        model.load_state_dict(checkpoint.state_dict)

        return cls(
            model=model,
            metadata=checkpoint.metadata,
            device=device,
        )
