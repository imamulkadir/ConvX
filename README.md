# ConvX - document conversion

**Simplification Stage 7:** one Next.js application invokes Python internally. No API connection, token, Redis, Celery or database setup is required. DOCX/PDF share source-verified analysis and separate Standard/EDGAR renderers. Supported conversions now produce validated downloadable ZIPs after actual browser checks. The final minimal UI and broader integration/cleanup remain later stages; known fidelity/EDGAR limits still apply.

## Run locally

Install Python 3.12+ and Node 22.19+, then from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m playwright install chromium
cd apps/web
npm.cmd ci
cd ../..
.\.venv\Scripts\python dev.py
```

Use an existing configured .venv when available. Open the URL printed by dev.py. Upload controls connect automatically; no token or local-access button. LibreOffice is the free native DOCX renderer; its workspace installation is detected when present. Renderer, input or analysis failures are reported honestly rather than shown as successful ZIPs.

## Current scope

DOCX is validated, tracked changes are accepted in a copy and free LibreOffice generates its visual-reference PDF. Uploaded PDFs are analyzed directly, without DOCX conversion or an extra reference upload. Standard .html uses embedded CSS/selectable SVG/local assets; EDGAR .htm uses restricted normal-flow markup and JPG/GIF. Successful jobs show Download ZIP; each source-basename archive contains only one document and its required assets at the root, with fresh download-time checks. The supplied complex fixtures still fail EDGAR clipping checks explicitly and receive no EDGAR ZIP. The final checkbox/minimal interface is Stage 8 and requires later authorization.

See [Standard renderer and limits](docs/standard-renderer.md), [shared layout contract](docs/shared-layout.md), [runtime/setup and limits](docs/simplified-runtime.md), [audit and staged plan](docs/refactor-audit.md), [project status](PROJECT_STATUS.md), [checkpoint](.agent-checkpoint.json), [agent instructions](AGENTS.md), [decisions](docs/decisions.md) and [test history](docs/test-history.md). Retired service source and existing user data remain preserved; do not start the old API/worker commands for the active application.

## Checks

Install requirements-dev.txt (or the verified Windows requirements-dev-lock.txt), then:

```powershell
.\.venv\Scripts\python -m pytest -q
cd apps/web
npm.cmd test
npm.cmd run test:ui
```

Tests use real local processes and regression fixtures, never simulated conversion success. No SEC acceptance or universal pixel-perfect fidelity is claimed. Git initialization/staging/committing/pushing and all other Git writes are prohibited for agents; review and Git changes belong to the user.
See [ZIP contract and download checks](docs/zip-packaging.md) and [EDGAR manual interpretation and limitations](docs/edgar-renderer.md). Standard remains default; the final EDGAR checkbox is pending Stage 8.
