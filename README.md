# ConvX — DOCX-to-HTM converter

Browser workspace for secure DOCX revision acceptance, PDF-first layout reconstruction, manual-derived EDGAR validation, all-page visual comparison and clean filing-asset ZIP download. Compliance and exact disclosure take priority; unresolved strict fidelity failures prevent download.

**Stage 9 UI is implemented.** With the configured API running, use `cd apps/web`, `npm.cmd ci`, then `npm.cmd run dev`. Open http://127.0.0.1:3000. See [frontend setup](docs/frontend.md) for connection, batch upload, progress, diagnostic PDF/HTM preview and download controls. Current validation failures still prevent a qualified filing ZIP. The paragraph below records the Stage 8 engine handoff.

**Current delivery: Stage 8 ZIP packaging.** Authenticated uploads, durable jobs, revision acceptance, free local LibreOffice PDF export and strict reference validation and a versioned PDF layout model are implemented. The supplied DOCX's accepted content matches its baseline; its generated 23-page PDF fails strict layout comparison and remains unsuccessful. Read-only inspection retains 85,798 reference characters without authorizing reconstruction. See [layout analysis](docs/pdf-layout-analysis.md). Private HTM candidates now preserve disclosure text and reconstruct supported flow/table layouts. Local actual-file SEC checks and source-bound JPG/GIF normalization are implemented. Unresolved CSS/MANY/character permissions fail strict validation; Pinned Chromium print/screen rendering and content/geometry/pixel comparison are implemented, with explicit strict failures for unresolved differences. Deterministic ZIP creation, independent archive audit and protected download checks are implemented. The Word reference remains unqualified; no successful full-chain download is demonstrated. The frontend remains Stage 9 work. See [ZIP packaging](docs/zip-packaging.md). See [visual validation](docs/visual-validation.md). See [SEC validation](docs/sec-validation-engine.md). See [HTM reconstruction](docs/htm-reconstruction.md). See [project status](PROJECT_STATUS.md), [checkpoint](.agent-checkpoint.json) and [agent instructions](AGENTS.md). No SEC acceptance or pixel-perfect conversion is claimed.

## Architecture and requirements

Next.js App Router with React JSX, Tailwind, DaisyUI and Lucide; Python FastAPI/Pydantic API; Redis/Celery workers; PostgreSQL job storage; private artifacts; PyMuPDF, Pillow, lxml and Playwright/Chromium conversion tooling. All implemented/planned components must be free to use: no premium SDK, trial renderer or paid service is included. See [architecture](docs/architecture.md), [contracts](docs/interfaces.md), [pipeline](docs/conversion-pipeline.md), [SEC constraints](docs/sec-compliance.md) and [limitations](docs/limitations.md).

## Stage 1 inspection and verification

Python 3.12 is the inspected environment. Use a private development environment; installation below is for read-only analysis tooling, not the eventual application:

```powershell
python -m venv .venv-analysis
.\.venv-analysis\Scripts\python -m pip install -r tools/requirements-analysis.txt
.\.venv-analysis\Scripts\python tools/inspect_references.py --output docs/fixture-inventory.json
python tools/verify_stage1.py
```

The inventory reads every PDF page and DOCX Word XML part and records hashes. It is not safe admission logic for arbitrary uploads. Use it only with the supplied trusted regression fixtures. Do not modify originals; review fixture changes explicitly and regenerate inventory after intentional replacements. [Reference findings](docs/reference-findings.md) explains identities and unresolved mappings. Test commands and actual results are recorded in [test history](docs/test-history.md).

## Development and operation

Follow [backend setup](docs/backend-development.md) and [document-processing setup](docs/docx-processing.md) for pinned installation, `.env`, schema initialization, FastAPI startup, independent Redis/Celery processes and real reference checks. Install both local API and converter packages. Workers accept supported revisions and render PDF when a trusted LibreOffice path is configured. Missing renderer/reference blocks processing; strict differences fail. Preview/download remain gated, and readiness still reports full conversion unavailable.

Stage 4 introduces the intermediate PDF layout model; Stage 9 builds the UI; Stage 10 integrates the full pipeline; Stage 11 supplies deployment files and process/network hardening. See [deployment design](docs/deployment.md). The Windows/SQLite/native-renderer suite does not certify Linux workers or live Redis/PostgreSQL deployments; optional real-service tests are included. Do not expose unfinished services as production-ready.

If inspection cannot import pypdf, use the analysis environment above. Missing fixtures must be located and verified, never replaced by fabricated test results. Read [decisions](docs/decisions.md) before changing a provider or compliance interpretation. Keep one stage per authorization; Git initialization, staging, committing, pushing and other Git writes are prohibited. Review and Git changes belong to the user.
