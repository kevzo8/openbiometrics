# OpenBiometrics

Open-source biometric platform for developers. Face recognition, document processing, liveness detection, video analytics, and identity verification — as simple as an API call.

**[Documentation](https://docs.openbiometrics.dev)** | **[Demo](https://demo.openbiometrics.dev)** | **[API Reference](https://docs.openbiometrics.dev/api/face-detection/)**

## Features

- **Face Detection** — YuNet detector with quality scoring, landmarks, demographics
- **Face Recognition** — SFace embeddings (99.4% LFW), 1:1 verification and 1:N identification
- **Passive Liveness** — MiniFASNet anti-spoofing, no user interaction
- **Active Liveness** — 6 presets (eye, smile, multi-range, head-turn, full, passive-only)
- **Document Processing** — MRZ parsing (ICAO 9303), OCR, document detection for passports/IDs
- **Video Analytics** — Multi-camera management with real-time face processing
- **Events & Webhooks** — Event bus with HMAC-signed webhook delivery
- **Watchlists** — FAISS-powered similarity search, identity resolution, deduplication
- **Edge Ready** — Docker, Jetson, ARM via ONNX Runtime / TensorRT

## Quick Start

```bash
git clone https://github.com/openbm/openbiometrics && cd openbiometrics
cd engine && pip install -e . && cd ..
python download_models.py --module face
cd api && uvicorn app.main:app --port 8000
```

```bash
curl -X POST http://localhost:8000/api/v1/detect -F "image=@photo.jpg"
```

## Models & Licensing

All default models are **fully open-source** (MIT / Apache 2.0). No commercial restrictions.

| Model | License | Size | Purpose | Accuracy |
|-------|---------|------|---------|----------|
| YuNet | MIT | 0.3 MB | Face detection | 0.88 AP (WIDER Face) |
| SFace | Apache 2.0 | 37 MB | Face recognition | 99.4% (LFW) |
| ViT GenderAge | Apache 2.0 | 330 MB | Age & gender | 94.3% gender, 4.5yr MAE |
| MiniFASNet | Apache 2.0 | 2 MB | Passive liveness | ~98% |
| YOLOv8n | AGPL-3.0 | 12 MB | Person detection | — |
| Face Mesh | Apache 2.0 | 2.8 MB | Active liveness | — |

### Model Tiers

OpenBiometrics supports three model tiers — check what's loaded via `GET /api/v1/admin/health`:

- **Community** — open-source models, commercial use OK, no restrictions (default)
- **Premium** — highest accuracy models from partners, requires license key
- **Legacy** — InsightFace models (non-commercial), kept for backward compatibility

```python
# Choose your models explicitly
FaceConfig(detector="yunet", recognizer="sface")           # community (default)
FaceConfig(detector="det_10g", recognizer="w600k_r50")     # legacy (non-commercial)
```

## Liveness Presets

Pre-configured liveness modes matching industry standards:

```bash
# Create session with a preset
curl -X POST "http://localhost:8000/api/v1/liveness/sessions?preset=smile"

# List all presets
curl http://localhost:8000/api/v1/liveness/presets
```

| Preset | Challenges | Use Case |
|--------|-----------|----------|
| `eye` | Blink x2 | Low-friction re-auth |
| `smile` | Smile x1 | Natural UX onboarding |
| `multi_range` | Blink + head turns x4 | High-security KYC |
| `head_turn` | Left + right x2 | Balanced security/UX |
| `full` | All types, randomized x4 | Maximum security |
| `passive_only` | None (MiniFASNet only) | Zero-friction |

## SDKs

### Node.js / TypeScript
```ts
import { OpenBiometrics } from 'openbiometrics';

const ob = new OpenBiometrics({ apiKey: 'any', baseUrl: 'http://localhost:8000' });
const { faces } = await ob.faces.detect(photoBuffer);
const { is_match } = await ob.faces.verify(id, selfie);
```

### Python
```python
from openbiometrics_sdk import OpenBiometrics

ob = OpenBiometrics(api_key="any", base_url="http://localhost:8000")
result = ob.faces.detect("photo.jpg")
result = ob.faces.verify("id.jpg", "selfie.jpg")
```

## Project Structure

```
openbiometrics/
├── VERSION              # Single source of truth for engine version
├── engine/              # Core biometric engine (Python)
│   └── openbiometrics/  # Face, documents, liveness, video, events, identity
├── api/                 # FastAPI REST server
├── packages/
│   ├── dashboard/       # React admin UI
│   ├── sdk/             # Node.js SDK (npm install openbiometrics)
│   ├── www/             # Documentation site (Astro + Starlight)
│   ├── sample-kyc/      # KYC onboarding demo
│   ├── sample-2fa/      # Face 2FA login demo
│   ├── sample-age-gate/ # Age verification demo
│   ├── sample-visitor-log/    # Visitor management demo
│   └── sample-surveillance/   # Surveillance dashboard demo
├── sdks/
│   └── python/          # Python SDK (pip install openbiometrics)
└── docs/                # Versioning strategy, architecture docs
```

## Development

```bash
mprocs --config mprocs.yaml   # Run all services
```

| Service | URL |
|---------|-----|
| API + Swagger | http://localhost:8000/docs |
| Dashboard | http://localhost:3600 |
| Docs | http://localhost:4000 |

## Version

Current: **0.3.0** — check at runtime via `GET /api/v1/admin/health` or `X-OpenBiometrics-Version` response header.

See [docs/versioning.md](docs/versioning.md) for the full versioning strategy.

## License

[MIT](LICENSE)
