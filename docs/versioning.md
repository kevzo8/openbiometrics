# Versioning & Release Strategy

OpenBiometrics uses [Semantic Versioning](https://semver.org/) (semver) across all components.

## Version Numbers

```
MAJOR.MINOR.PATCH
  0  .  3  .  0
```

- **PATCH** (0.3.0 → 0.3.1) — Bug fixes. Safe to upgrade.
- **MINOR** (0.3.0 → 0.4.0) — New features, backward compatible. Safe to upgrade.
- **MAJOR** (0.3.0 → 1.0.0) — Breaking changes. Read the migration guide.

## Components & Independent Versioning

Each component has its own version and release cycle:

| Component | Package | Current | Description |
|-----------|---------|---------|-------------|
| **Engine + API** | `openbiometrics-engine` (PyPI) | `VERSION` file | Core biometric engine and REST server. Single version. |
| **JS/TS SDK** | `openbiometrics` (npm) | `packages/sdk/package.json` | Client library for JavaScript/TypeScript apps. |
| **Python SDK** | `openbiometrics-sdk` (PyPI) | `sdks/python/pyproject.toml` | Client library for Python apps. |
| **Dashboard** | `@openbiometrics/dashboard` (private) | `packages/dashboard/package.json` | Web UI, ships with API server. |
| **Docs** | `@openbiometrics/www` (private) | `packages/www/package.json` | Documentation site. |

### Why Independent Versions?

Components move at different speeds:

- **Engine** changes when algorithms or API endpoints change
- **SDKs** change when they add convenience methods or fix client-side bugs
- **Dashboard** changes for UI improvements that don't affect the API

A SDK bug fix shouldn't force an engine version bump. An engine feature addition shouldn't force a SDK release if the SDK doesn't use it yet.

## Compatibility Contract

Each SDK declares the **minimum API version** it requires:

```python
# Python SDK
from openbiometrics_sdk import MIN_API_VERSION  # "0.3.0"
```

```typescript
// JS SDK (package.json)
"openbiometrics": { "minApiVersion": "0.3.0" }
```

SDKs check compatibility on initialization:

```python
ob = OpenBiometrics(api_key="...")
# Calls GET /api/v1/admin/health → {"version": "0.3.0", ...}
# Compares server version against MIN_API_VERSION
# Warns if server is too old
```

### Compatibility Matrix

| SDK Version | Min API Version | Notes |
|-------------|-----------------|-------|
| Python SDK 0.1.x | API >= 0.3.0 | Initial release |
| JS SDK 0.1.x | API >= 0.3.0 | Initial release |

## Version Discovery

Adopters can check the version at every layer:

```bash
# Package manager
pip show openbiometrics-engine    # Version: 0.3.0
npm info openbiometrics version   # 0.1.0

# Python runtime
python -c "import openbiometrics; print(openbiometrics.__version__)"

# API server
curl http://localhost:8000/api/v1/admin/health
# {"version": "0.3.0", "healthy": true, "modules": {...}}

# HTTP response header (every response)
# X-OpenBiometrics-Version: 0.3.0
```

## Source of Truth

```
/VERSION                          → Engine + API version (e.g., "0.3.0")
/packages/sdk/package.json        → JS SDK version
/sdks/python/pyproject.toml       → Python SDK version
/engine/openbiometrics/__init__.py → reads /VERSION at runtime
```

## Release Process

### Engine + API Release

1. Update `/VERSION` with new version
2. Update `engine/pyproject.toml` and `api/pyproject.toml` to match
3. Update `packages/dashboard/package.json` to match (ships with API)
4. Write changelog entry in `CHANGELOG.md`
5. Tag: `git tag v0.4.0`
6. Build and publish: `pip publish`, Docker image

### SDK Release

1. Update version in `packages/sdk/package.json` or `sdks/python/pyproject.toml`
2. Update `MIN_API_VERSION` if new features require a newer API
3. Update compatibility matrix in this doc
4. Tag: `git tag sdk-js-v0.2.0` or `git tag sdk-py-v0.2.0`
5. Publish: `npm publish` or `pip publish`

### Rules

- Engine MINOR bump = SDK should still work (backward compatible)
- Engine MAJOR bump = SDKs must update `MIN_API_VERSION` and may need code changes
- SDK can release independently of engine
- Dashboard versions track engine (ships together)
- Never break a PATCH or MINOR release. If you did, yank it and release a new PATCH.

## For Innovatrics Comparison

This is how DIS v1.63.0 + Android SDK v9.2.0 + Web Components v8.0.4 should work — but with an explicit, machine-checkable compatibility contract instead of a manual version matrix page. The SDK tells you at runtime if your server is too old. No guessing.
