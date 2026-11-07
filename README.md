# ConvX - document conversion

**Simplification Stage 10:** one Next.js application invokes Python internally. Open its focused single-document form, choose DOCX/PDF, optionally enable SEC EDGAR Compliance, then convert and download ZIP. No API connection, token, Redis, Celery or database setup is required. Supported outputs have real browser and package checks; known fidelity/EDGAR limits remain. All ten stages are complete within documented supported local cases. See [final review and limits](docs/stage10-review.md), [integration results](docs/integration-testing.md) and [current recovery](docs/edgar-fix-resume.md).

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

DOCX is validated, tracked changes are accepted in a copy and free LibreOffice generates its visual-reference PDF. Uploaded PDFs are analyzed directly. Standard is the unchecked default and produces .html; the EDGAR checkbox produces restricted .htm/JPG/GIF for supported layouts. The page shows real progress, source-basename ZIP filename and Download ZIP, with optional notes and visual comparison. Reload recovers the current conversion; Convert another document clears its temporary files and resets the form. Each archive contains only one document and referenced root assets, with fresh download checks. The supplied complex DOCX/PDF fixtures now have a tested rectangular EDGAR reconstruction path with explicit sidebar reflow/visibility notes; curved and unsupported geometry still fail clearly. See [repair details](docs/edgar-rectangular-layout.md).

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
See [interface guide](docs/simple-interface.md), [ZIP contract](docs/zip-packaging.md) and [EDGAR manual interpretation/limits](docs/edgar-renderer.md). Restart the local development server after updating application code.
