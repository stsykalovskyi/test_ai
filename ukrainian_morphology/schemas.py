"""Pydantic schemas describing morphology inputs and outputs."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import CASES, CASE_ALIASES, GENDERS, ANIMACY


def normalise_case(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in CASES:
        return lowered
    if lowered in CASE_ALIASES:
        return CASE_ALIASES[lowered]
    raise ValueError("Unsupported grammatical case")


class InflectRequest(BaseModel):
    """Incoming payload describing the desired inflection."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    lemma: str = Field(min_length=1, description="Base form of the name or title")
    case: str = Field(alias="target_case", description="Target grammatical case")
    gender: Optional[str] = Field(default=None, description="Grammatical gender hint")
    animacy: Optional[str] = Field(default=None, description="Animacy flag if relevant")
    title: Optional[str] = Field(default=None, description="Honorific or rank to inflect alongside the name")

    @field_validator("lemma")
    @classmethod
    def _clean_lemma(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Lemma must not be empty")
        return cleaned

    @field_validator("case")
    @classmethod
    def _validate_case(cls, value: str) -> str:
        return normalise_case(value)

    @field_validator("gender")
    @classmethod
    def _validate_gender(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        lowered = value.strip().lower()
        if lowered not in GENDERS:
            raise ValueError("Unsupported gender value")
        return lowered

    @field_validator("animacy")
    @classmethod
    def _validate_animacy(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        lowered = value.strip().lower()
        if lowered not in ANIMACY:
            raise ValueError("Unsupported animacy flag")
        return lowered


class InflectionResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    lemma: str
    target_case: str
    inflected: str
    gender: Optional[str] = None
    animacy: Optional[str] = None
    title: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
