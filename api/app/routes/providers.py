"""Cloud provider endpoints — proxy face operations to AWS, Azure, or Google.

Same response format as local endpoints, different engine under the hood.
"""

from __future__ import annotations

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from openbiometrics.providers import get_provider, list_providers
from openbiometrics.providers.base import CloudProvider

router = APIRouter()

# Cache provider instances per name+config
_provider_cache: dict[str, CloudProvider] = {}


def _get_or_create_provider(
    name: str,
    region: str | None = None,
    endpoint: str | None = None,
    api_key: str | None = None,
) -> CloudProvider:
    """Get cached provider or create new one."""
    cache_key = f"{name}:{region}:{endpoint}:{api_key and api_key[:8]}"
    if cache_key not in _provider_cache:
        kwargs = {}
        if name == "aws":
            if region:
                kwargs["region"] = region
        elif name == "azure":
            if not endpoint or not api_key:
                raise HTTPException(400, "Azure requires endpoint and api_key parameters")
            kwargs["endpoint"] = endpoint
            kwargs["api_key"] = api_key
        elif name == "google":
            if not api_key:
                raise HTTPException(400, "Google requires api_key parameter")
            kwargs["api_key"] = api_key

        try:
            _provider_cache[cache_key] = get_provider(name, **kwargs)
        except ImportError as e:
            raise HTTPException(501, str(e))
        except KeyError as e:
            raise HTTPException(400, str(e))

    return _provider_cache[cache_key]


@router.get("/")
async def list_available_providers():
    """List all available cloud providers with features and pricing."""
    return list_providers()


@router.post("/{provider_name}/detect")
async def cloud_detect(
    provider_name: str,
    image: UploadFile = File(...),
    max_faces: int = Query(10),
    demographics: bool = Query(True),
    emotions: bool = Query(False),
    quality: bool = Query(False),
    region: str | None = Query(None),
    endpoint: str | None = Query(None),
    api_key: str | None = Query(None),
):
    """Detect faces using a cloud provider.

    Same response format as /api/v1/faces/detect, different engine.
    """
    provider = _get_or_create_provider(provider_name, region, endpoint, api_key)
    image_bytes = await image.read()

    try:
        results = provider.detect(
            image_bytes,
            max_faces=max_faces,
            include_demographics=demographics,
            include_emotions=emotions,
            include_quality=quality,
        )
    except Exception as e:
        raise HTTPException(502, f"Provider {provider_name} error: {e}")

    return {
        "provider": provider_name,
        "count": len(results),
        "faces": [
            {
                "bbox": r.bbox,
                "confidence": r.confidence,
                "landmarks": r.landmarks,
                "demographics": {"age": r.age, "gender": r.gender} if r.age or r.gender else None,
                "emotions": r.emotions,
                "quality": {"overall_score": r.quality_score} if r.quality_score else None,
                "liveness": None,
            }
            for r in results
        ],
    }


@router.post("/{provider_name}/compare")
async def cloud_compare(
    provider_name: str,
    image1: UploadFile = File(...),
    image2: UploadFile = File(...),
    region: str | None = Query(None),
    endpoint: str | None = Query(None),
    api_key: str | None = Query(None),
):
    """Compare two faces using a cloud provider (1:1 verification)."""
    provider = _get_or_create_provider(provider_name, region, endpoint, api_key)

    bytes1 = await image1.read()
    bytes2 = await image2.read()

    try:
        result = provider.compare(bytes1, bytes2)
    except NotImplementedError as e:
        raise HTTPException(501, str(e))
    except Exception as e:
        raise HTTPException(502, f"Provider {provider_name} error: {e}")

    return {
        "provider": provider_name,
        "is_match": result.is_match,
        "similarity": result.similarity,
    }


@router.get("/{provider_name}/health")
async def cloud_health(
    provider_name: str,
    region: str | None = Query(None),
    endpoint: str | None = Query(None),
    api_key: str | None = Query(None),
):
    """Check cloud provider connectivity."""
    provider = _get_or_create_provider(provider_name, region, endpoint, api_key)
    return provider.health()
