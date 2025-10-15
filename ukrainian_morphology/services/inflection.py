"""Service layer for handling Ukrainian name and title inflection."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from django.conf import settings

from ..constants import CASES
from ..schemas import InflectRequest, InflectionResult
from ml.models.inflector import InflectorModel


@dataclass
class MorphologicalInflector:
    """Facade for loading and executing morphological models.

    Uses a simple frequency-based model when a trained checkpoint is available,
    otherwise falls back to a rule-based mock implementation.
    """

    model_path: Optional[str] = None
    model: InflectorModel = field(init=False, default_factory=InflectorModel)

    def __post_init__(self):
        self.checkpoint_path = self._resolve_model_path()
        if self.checkpoint_path and self.checkpoint_path.exists():
            try:
                self.model = InflectorModel.load(self.checkpoint_path)
            except Exception:  # pragma: no cover - corrupted checkpoint
                self.model = InflectorModel()

    def inflect(self, payload: InflectRequest) -> InflectionResult:
        predicted = self.model.predict(
            lemma=payload.lemma,
            target_case=payload.case,
            gender=payload.gender,
            animacy=payload.animacy,
            title=payload.title,
        )
        if predicted:
            confidence = 1.0
            inflected = predicted
        else:
            confidence = 0.0
            inflected = self._fallback_inflection(payload)

        return InflectionResult(
            lemma=payload.lemma,
            target_case=payload.case,
            inflected=inflected,
            gender=payload.gender,
            animacy=payload.animacy,
            title=payload.title,
            confidence=confidence,
        )

    def _fallback_inflection(self, payload: InflectRequest) -> str:
        if payload.case == "називний":
            return payload.lemma
        suffix = CASES[payload.case]
        parts = [payload.lemma, f"[{suffix}]"]
        if payload.title:
            parts.append(payload.title)
        return " ".join(parts)

    def _resolve_model_path(self) -> Optional[Path]:
        if self.model_path:
            return Path(self.model_path)
        default_path = Path(settings.ARTIFACTS_DIR) / "ukrainian-inflector" / "checkpoints" / "latest.json"
        return default_path if default_path.exists() else None
