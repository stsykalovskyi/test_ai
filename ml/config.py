"""Configuration helpers for training pipelines."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator

from test_ai.settings import ARTIFACTS_DIR, DATA_DIR, MODEL_CACHE_DIR


class TrainingConfig(BaseModel):
    """High-level configuration for training an inflection model."""

    model_config = ConfigDict(extra="forbid")

    experiment_name: str = Field(default="ukrainian-inflector")
    seed: int = Field(default=42, ge=0)
    accelerator: Literal["cpu", "gpu"] = Field(default="cpu")
    max_epochs: int = Field(default=10, ge=1)
    batch_size: int = Field(default=32, ge=1)
    learning_rate: float = Field(default=5e-4, gt=0)
    cases: Sequence[str] = Field(default=("називний", "родовий", "давальний", "знахідний", "орудний", "місцевий", "кличний"))
    train_path: Path = Field(default=DATA_DIR / "processed" / "train.csv")
    dev_path: Path = Field(default=DATA_DIR / "processed" / "dev.csv")
    test_path: Path = Field(default=DATA_DIR / "processed" / "test.csv")
    artifacts_dir: Path = Field(default=ARTIFACTS_DIR)
    model_cache_dir: Path = Field(default=MODEL_CACHE_DIR)

    @field_validator("artifacts_dir", "model_cache_dir", "train_path", "dev_path", "test_path")
    @classmethod
    def ensure_parents(cls, value: Path) -> Path:
        if value.suffix:
            value.parent.mkdir(parents=True, exist_ok=True)
        else:
            value.mkdir(parents=True, exist_ok=True)
        return value

    @field_validator("cases")
    @classmethod
    def ensure_cases_not_empty(cls, value: Sequence[str]) -> Sequence[str]:
        if not value:
            raise ValueError("At least one grammatical case is required")
        return value

    @property
    def checkpoints_dir(self) -> Path:
        path = self.artifacts_dir / self.experiment_name / "checkpoints"
        path.mkdir(parents=True, exist_ok=True)
        return path
