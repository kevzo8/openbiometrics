#!/usr/bin/env python3
"""Download OpenBiometrics models.

Usage:
    python download_models.py                    # Download all models
    python download_models.py --module face      # Face detection + recognition models only
    python download_models.py --module document   # Document / OCR models only
    python download_models.py --module person     # Person detection models only
    python download_models.py --module all        # All models (default)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add the engine package to the path so we can import the registry
sys.path.insert(0, str(Path(__file__).parent / "engine"))

from openbiometrics.runtime.registry import ModelRegistry

# Which models belong to each module
_MODULE_MODELS: dict[str, list[str]] = {
    "face": ["yunet", "sface", "vit_genderage", "antispoofing"],
    "document": ["face_mesh"],
    "person": ["yolov8n"],
}


def _resolve_modules(module: str) -> list[str]:
    """Resolve module name to a list of model names."""
    if module == "all":
        models: list[str] = []
        for group in _MODULE_MODELS.values():
            for m in group:
                if m not in models:
                    models.append(m)
        return models
    if module not in _MODULE_MODELS:
        available = ", ".join(sorted(_MODULE_MODELS.keys()))
        print(f"Error: unknown module '{module}'. Available: {available}, all")
        sys.exit(1)
    return _MODULE_MODELS[module]


def main() -> None:
    parser = argparse.ArgumentParser(description="Download OpenBiometrics models")
    parser.add_argument(
        "--module",
        default="all",
        choices=["face", "document", "person", "all"],
        help="Which module's models to download (default: all)",
    )
    parser.add_argument(
        "--models-dir",
        default="./models",
        help="Directory to store models (default: ./models)",
    )
    args = parser.parse_args()

    registry = ModelRegistry(models_dir=args.models_dir)
    model_names = _resolve_modules(args.module)

    print(f"Downloading models for module: {args.module}")
    print(f"Models directory: {Path(args.models_dir).resolve()}\n")

    for name in model_names:
        info = registry.list_models()
        model_info = next((m for m in info if m.name == name), None)
        if model_info is None:
            print(f"  [SKIP] {name} — not in model catalog")
            continue

        if registry.is_available(name):
            print(f"  [OK]   {name} — already downloaded")
        else:
            print(f"  [DL]   {name} — downloading ({model_info.size_mb:.1f} MB) ...")
            registry.ensure_model(name)
            print(f"         {name} — done")

    print("\nAll requested models are ready.")


if __name__ == "__main__":
    main()
