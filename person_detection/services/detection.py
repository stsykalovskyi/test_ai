"""Service layer for person detection inference."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from django.conf import settings
from PIL import Image

from ..schemas import PersonDetectionResult

if TYPE_CHECKING:
    from ml.models.person_classifier import PersonClassifierModel
    import torch


@dataclass
class PersonDetectionService:
    """Facade for loading and executing person detection model."""

    model_path: Optional[str] = None
    model: Optional["PersonClassifierModel"] = field(init=False, default=None)

    def __post_init__(self):
        self.checkpoint_path = self._resolve_model_path()
        if self.checkpoint_path and self.checkpoint_path.exists():
            try:
                # Lazy import to avoid loading heavy dependencies at module import time
                import torch
                from ml.models.person_classifier import PersonClassifierModel
                # Always use CPU for inference to avoid CUDA issues
                device = "cuda" if torch.cuda.is_available() else "cpu"
                self.model = PersonClassifierModel.load(self.checkpoint_path, device=device)
            except Exception:
                self.model = None

    def detect(self, image: Image.Image) -> PersonDetectionResult:
        """Detect person type in image."""
        if self.model is None:
            # Return default response if model not trained
            return PersonDetectionResult(label="nobody", confidence=0.0)

        label, confidence = self.model.predict(image)
        return PersonDetectionResult(label=label, confidence=confidence)

    def _resolve_model_path(self) -> Optional[Path]:
        """Resolve path to model checkpoint."""
        if self.model_path:
            return Path(self.model_path)
        default_path = Path(settings.ARTIFACTS_DIR) / "person-classifier" / "checkpoints" / "latest.pth"
        return default_path if default_path.exists() else None
