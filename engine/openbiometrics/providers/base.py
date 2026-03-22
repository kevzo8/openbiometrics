"""Base interface for cloud face processing providers.

All providers implement the same interface so they're interchangeable.
The pipeline doesn't care if faces come from local ONNX or AWS Rekognition.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np


@dataclass
class CloudFaceResult:
    """Standardized face result from any provider."""

    bbox: list[float]  # [x1, y1, x2, y2] normalized 0-1
    confidence: float
    landmarks: list[list[float]] | None = None
    age: int | None = None
    gender: str | None = None  # "M" or "F"
    embedding: list[float] | None = None
    is_live: bool | None = None
    liveness_score: float | None = None
    quality_score: float | None = None
    emotions: dict[str, float] | None = None
    # Provider-specific metadata
    provider: str = ""
    raw_response: dict | None = field(default=None, repr=False)


@dataclass
class CompareResult:
    """Result of comparing two faces."""

    is_match: bool
    similarity: float  # 0-1
    provider: str = ""


@dataclass
class SearchResult:
    """Result of searching a face against a collection."""

    face_id: str
    similarity: float
    label: str | None = None
    provider: str = ""


class CloudProvider(ABC):
    """Abstract base for cloud face processing providers."""

    name: str = "base"

    @abstractmethod
    def detect(
        self,
        image: bytes,
        *,
        max_faces: int = 10,
        include_demographics: bool = True,
        include_quality: bool = False,
        include_emotions: bool = False,
    ) -> list[CloudFaceResult]:
        """Detect faces in an image.

        Args:
            image: JPEG/PNG bytes
            max_faces: Maximum faces to return
            include_demographics: Include age/gender estimation
            include_quality: Include face quality metrics
            include_emotions: Include emotion classification

        Returns:
            List of detected faces with requested attributes
        """

    @abstractmethod
    def compare(self, image1: bytes, image2: bytes) -> CompareResult:
        """Compare two face images for verification (1:1).

        Args:
            image1: First face image (JPEG/PNG bytes)
            image2: Second face image (JPEG/PNG bytes)

        Returns:
            CompareResult with match verdict and similarity score
        """

    def check_liveness(self, image: bytes) -> tuple[bool, float]:
        """Check if a face image is live (not a spoof).

        Not all providers support this. Default raises NotImplementedError.

        Returns:
            (is_live, confidence)
        """
        raise NotImplementedError(f"{self.name} does not support liveness detection")

    def health(self) -> dict:
        """Check provider connectivity and return status."""
        return {"provider": self.name, "status": "unknown"}
