# ConvX — DOCX-to-HTM converter

Planned browser application for secure DOCX revision acceptance, PDF-first layout reconstruction, manual-derived EDGAR validation, all-page visual comparison and clean filing-asset ZIP download. Compliance and exact disclosure take priority; unresolved strict fidelity failures prevent download.

**Current delivery: Stage 2 backend foundation.** Authenticated uploads, durable jobs, polling/events, private storage, dispatch and admission workers are implemented. Conversion engines, the frontend and filing downloads are not available yet. See [project status](PROJECT_STATUS.md), [checkpoint](.agent-checkpoint.json) and [agent instructions](AGENTS.md). No conversion results or SEC acceptance are claimed.

## Architecture and requirements

Next.js App Router with React JSX, Tailwind, DaisyUI and Lucide; Python FastAPI/Pydantic API; Redis/Celery workers; PostgreSQL job storage; private artifacts; PyMuPDF, Pillow, lxml and Playwright/Chromium conversion tooling. Rendering is a separate provider boundary requiring licensing and fidelity qualification. See [architecture](docs/architecture.md), [contracts](docs/interfaces.md), [pipeline](docs/conversion-pipeline.md), [SEC constraints](docs/sec-compliance.md) and [limitations](docs/limitations.md).

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

Follow [backend setup and commands](docs/backend-development.md) for pinned installation, `.env`, schema initialization, FastAPI startup, independent Redis/Celery processes and tests. The API can receive documents; workers validate source integrity and report `PIPELINE_NOT_AVAILABLE` at the current capability boundary. Preview/download remain gated. Readiness accurately reports conversion unavailable.

Stage 3 introduces revision acceptance/PDF export; Stage 9 builds the UI; Stage 10 integrates the full pipeline; Stage 11 supplies deployment files and process/network hardening. See [deployment design](docs/deployment.md). The Windows/SQLite suite does not certify Linux workers or live Redis/PostgreSQL deployments; optional real-service tests are included. Do not expose unfinished services as production-ready.

If inspection cannot import pypdf, use the analysis environment above. Missing fixtures must be located and verified, never replaced by fabricated test results. Read [decisions](docs/decisions.md) before changing a provider or compliance interpretation. Keep one stage per authorization; Git initialization, staging, committing, pushing and other Git writes are prohibited. Review and Git changes belong to the user.
