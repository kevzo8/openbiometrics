# OpenBiometrics — Agent Instructions

## Versioning

**Unified semver** — one version for the entire platform, stored in `/VERSION`.

To bump: edit `/VERSION`, then run `pnpm version:sync`. Never hardcode version strings in individual packages.

All Python packages read `/VERSION` at runtime. JS packages are synced via the `version:sync` script. The API exposes version via `X-OpenBiometrics-Version` response header and `GET /api/v1/health`.

See memory `project_versioning.md` for the full release checklist.

## Project Structure

Monorepo with pnpm workspaces + Python packages:
- `engine/` — Core biometric engine (Python, InsightFace/ONNX)
- `api/` — FastAPI REST server
- `packages/sdk/` — TypeScript SDK
- `packages/dashboard/` — React admin dashboard
- `packages/www/` — Astro documentation site
- `packages/sample-2fa/` — Sample app: face-based 2FA demo
- `sdks/python/` — Python SDK

## Dev Servers

**Do NOT run `bun run dev`, `pnpm dev`, or any dev server automatically.** The user runs these manually.

## Tailwind CSS 4

**Do NOT use `@apply`** — it doesn't work in Tailwind CSS 4. Use inline classes directly.
