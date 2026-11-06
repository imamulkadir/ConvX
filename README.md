# ConvX - document conversion

**Simplification Stage 2:** one Next.js application invokes Python internally. No API connection, token, Redis, Celery or database setup is required. Existing secure DOCX processing is retained; PDF upload and the revised Standard/EDGAR renderers are pending their stages. The application is not yet a qualified end-to-end converter.

## Run locally

Install Python 3.12+ and Node 22.19+, then from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
cd apps/web
npm.cmd ci
cd ../..
.\.venv\Scripts\python dev.py
```

Use an existing configured .venv when available. Open the URL printed by dev.py. Upload controls connect automatically; no token or local-access button. LibreOffice is the free native DOCX renderer; its workspace installation is detected when present. Renderer, reference or fidelity failures are reported honestly rather than shown as successful ZIPs.

## Current scope

The architecture is simplified and tested. The old routine reference-PDF requirement still blocks a bare DOCX; direct PDF and Standard .html are not implemented yet. The revised final contract is Standard .html by default, optional EDGAR .htm, with one document and exactly its referenced assets in the ZIP root. Each later stage requires explicit authorization.

See [runtime/setup and limits](docs/simplified-runtime.md), [audit and staged plan](docs/refactor-audit.md), [project status](PROJECT_STATUS.md), [checkpoint](.agent-checkpoint.json), [agent instructions](AGENTS.md), [decisions](docs/decisions.md) and [test history](docs/test-history.md). Retired service source and existing user data remain preserved; do not start the old API/worker commands for the active application.

## Checks

Install requirements-dev.txt (or the verified Windows requirements-dev-lock.txt), then:

```powershell
.\.venv\Scripts\python -m pytest -q
cd apps/web
npm.cmd test
npm.cmd run test:ui
```

Tests use real local processes and regression fixtures, never simulated conversion success. No SEC acceptance or universal pixel-perfect fidelity is claimed. Git initialization/staging/committing/pushing and all other Git writes are prohibited for agents; review and Git changes belong to the user.
