# Release Agent

Manages version bumps and release preparation for OpenBiometrics.

## Usage

```
/release engine patch    # 0.3.0 → 0.3.1
/release engine minor    # 0.3.0 → 0.4.0
/release engine major    # 0.3.0 → 1.0.0
/release sdk-js patch    # bump JS SDK
/release sdk-py patch    # bump Python SDK
/release status          # show all current versions + compatibility
```

## Behavior

### Engine Release (engine + API + dashboard)

1. Read current version from `/VERSION`
2. Compute new version based on bump type (patch/minor/major)
3. Update all engine version locations:
   - `/VERSION`
   - `/engine/pyproject.toml`
   - `/api/pyproject.toml`
   - `/packages/dashboard/package.json`
4. If MAJOR bump, prompt user: "This is a breaking change. What changed?"
5. Prepend entry to `CHANGELOG.md`
6. Show diff summary and ask user to confirm before committing

### JS SDK Release

1. Read current version from `/packages/sdk/package.json`
2. Compute new version
3. Ask: "Does this require a newer API version? Current min: X"
4. If yes, update `minApiVersion` in package.json
5. Update compatibility matrix in `/docs/versioning.md`
6. Prepend entry to `CHANGELOG.md`
7. Show diff and confirm

### Python SDK Release

1. Read current version from `/sdks/python/pyproject.toml`
2. Compute new version
3. Ask: "Does this require a newer API version? Current min: X"
4. If yes, update `MIN_API_VERSION` in `/sdks/python/openbiometrics_sdk/__init__.py`
5. Update compatibility matrix in `/docs/versioning.md`
6. Prepend entry to `CHANGELOG.md`
7. Show diff and confirm

### Status

Show a table of all component versions and their compatibility:

```
Component          Version   Min API   Status
─────────────────────────────────────────────
Engine + API       0.3.0     —         source of truth
JS SDK             0.1.0     >= 0.3.0  ✓ compatible
Python SDK         0.1.0     >= 0.3.0  ✓ compatible
Dashboard          0.3.0     —         ships with API
Docs               0.3.0     —         ships with API
```

## Rules

- Never skip versions (0.3.0 → 0.5.0). Always increment by 1.
- CHANGELOG.md is mandatory for every release.
- For engine MAJOR bumps, check if SDKs need MIN_API_VERSION updates.
- Git tag format: `v0.4.0` (engine), `sdk-js-v0.2.0`, `sdk-py-v0.2.0`.
- Don't push tags automatically — let the user decide when to push.
