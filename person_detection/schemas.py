"""Pydantic schemas for person detection API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PersonLabel = Literal["man", "woman", "nobody"]


class PersonDetectionRequest(BaseModel):
    """Request for person detection from image data."""

    model_config = ConfigDict(extra="forbid")

    # Base64-encoded image will be sent in the request
    # In actual API, we'll handle file upload via multipart/form-data


class PersonDetectionResult(BaseModel):
    """Result of person detection."""

    model_config = ConfigDict()

    label: PersonLabel = Field(description="Detected person type: man, woman, or nobody")
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence score")
