"""Cloud provider backends for face processing.

OpenBiometrics can use local ONNX models (default) or proxy to cloud providers
for higher accuracy. Same API, different engine — user switches with one config line.

Providers:
    local    — ONNX models running locally (default, free, open-source)
    aws      — Amazon Rekognition
    azure    — Microsoft Azure Face API
    google   — Google Cloud Vision (face detection only)

Usage:
    from openbiometrics.providers import get_provider

    provider = get_provider("aws", credentials={"region": "us-east-1"})
    faces = provider.detect(image)
    similarity = provider.compare(image1, image2)
"""

from openbiometrics.providers.base import CloudProvider, CloudFaceResult
from openbiometrics.providers.registry import get_provider, list_providers

__all__ = [
    "CloudProvider",
    "CloudFaceResult",
    "get_provider",
    "list_providers",
]
