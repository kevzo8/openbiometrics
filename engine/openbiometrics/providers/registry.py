"""Provider registry — factory for cloud backends.

Usage:
    from openbiometrics.providers import get_provider

    # AWS
    provider = get_provider("aws", region="us-east-1")

    # Azure
    provider = get_provider("azure",
        endpoint="https://your-resource.cognitiveservices.azure.com",
        api_key="your-key",
    )

    # Google
    provider = get_provider("google", api_key="your-key")
"""

from __future__ import annotations

from openbiometrics.providers.base import CloudProvider


_PROVIDER_FACTORIES: dict[str, type] = {}


def _register_lazy():
    """Register providers lazily to avoid import errors when deps aren't installed."""
    global _PROVIDER_FACTORIES
    if _PROVIDER_FACTORIES:
        return

    _PROVIDER_FACTORIES = {
        "aws": "openbiometrics.providers.aws:AWSProvider",
        "azure": "openbiometrics.providers.azure:AzureProvider",
        "google": "openbiometrics.providers.google:GoogleProvider",
    }


def get_provider(name: str, **kwargs) -> CloudProvider:
    """Create a cloud provider by name.

    Args:
        name: Provider name ("aws", "azure", "google")
        **kwargs: Provider-specific configuration (passed to constructor)

    Returns:
        Configured CloudProvider instance

    Raises:
        KeyError: If provider name is unknown
        ImportError: If provider dependencies aren't installed
    """
    _register_lazy()

    if name not in _PROVIDER_FACTORIES:
        available = ", ".join(sorted(_PROVIDER_FACTORIES.keys()))
        raise KeyError(f"Unknown provider '{name}'. Available: {available}")

    ref = _PROVIDER_FACTORIES[name]

    if isinstance(ref, str):
        # Lazy import: "module.path:ClassName"
        module_path, class_name = ref.rsplit(":", 1)
        import importlib
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        _PROVIDER_FACTORIES[name] = cls
    else:
        cls = ref

    return cls(**kwargs)


def list_providers() -> list[dict]:
    """List available providers with their requirements."""
    return [
        {
            "name": "aws",
            "description": "Amazon Rekognition — face detection, recognition, comparison",
            "install": "pip install boto3",
            "features": ["detect", "compare", "demographics", "emotions"],
            "pricing": "$0.001/image (first 1M)",
        },
        {
            "name": "azure",
            "description": "Microsoft Azure Face API — face detection, recognition, verification",
            "install": "pip install (no extra deps, uses urllib)",
            "features": ["detect", "compare", "demographics", "emotions", "quality"],
            "pricing": "Free: 30K/mo, Standard: tiered",
        },
        {
            "name": "google",
            "description": "Google Cloud Vision — face detection only (no recognition)",
            "install": "pip install (no extra deps, uses urllib)",
            "features": ["detect", "emotions"],
            "pricing": "$1.50 per 1,000 images",
        },
    ]
