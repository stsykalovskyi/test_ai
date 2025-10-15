"""Model definition and serialization helpers for the Ukrainian inflector."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from collections import Counter, defaultdict

from ..datasets.ukrainian_names import MorphologySample


Key = Tuple[str, str, str, str, str]


@dataclass
class InflectorCheckpoint:
    mapping: Dict[Key, str]
    metadata: dict[str, Any]

    def to_json(self) -> str:
        serializable = {
            "mapping": {"|".join(key): value for key, value in self.mapping.items()},
            "metadata": self.metadata,
        }
        return json.dumps(serializable, ensure_ascii=False, indent=2)

    @classmethod
    def from_path(cls, path: Path) -> "InflectorCheckpoint":
        payload = json.loads(path.read_text(encoding="utf-8"))
        mapping = {
            tuple(key.split("|")): value for key, value in payload["mapping"].items()
        }
        return cls(mapping=mapping, metadata=payload.get("metadata", {}))


@dataclass
class InflectorModel:
    """Simple frequency-based model that memorises inflections from training data."""

    mapping: Dict[Key, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def fit(self, samples: Iterable[MorphologySample]) -> None:
        counts: dict[Key, Counter] = defaultdict(Counter)
        total = 0
        for sample in samples:
            key = self._build_key(sample)
            counts[key][sample.inflected] += 1
            total += 1
        if not total:
            raise ValueError("Training dataset is empty")
        self.mapping = {
            key: counter.most_common(1)[0][0] for key, counter in counts.items()
        }
        self.metadata = {"samples": total, "unique_patterns": len(self.mapping)}

    def predict(self, lemma: str, target_case: str, gender: str | None = None, animacy: str | None = None, title: str | None = None) -> str | None:
        key = self._build_key_from_strings(lemma, target_case, gender, animacy, title)
        return self.mapping.get(key)

    def load_checkpoint(self, checkpoint: InflectorCheckpoint) -> None:
        self.mapping = checkpoint.mapping
        self.metadata = checkpoint.metadata

    def export(self) -> InflectorCheckpoint:
        return InflectorCheckpoint(mapping=self.mapping, metadata=self.metadata)

    @staticmethod
    def _build_key(sample: MorphologySample) -> Key:
        return (sample.lemma.lower().strip(), sample.target_case, sample.gender or "", sample.animacy or "", sample.title or "")

    @staticmethod
    def _build_key_from_strings(lemma: str, case: str, gender: str | None, animacy: str | None, title: str | None) -> Key:
        return (lemma.lower().strip(), case, gender or "", animacy or "", title or "")

    def save(self, path: Path) -> Path:
        path.write_text(self.export().to_json(), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> "InflectorModel":
        checkpoint = InflectorCheckpoint.from_path(path)
        model = cls()
        model.load_checkpoint(checkpoint)
        return model
