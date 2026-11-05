# ConvX — EDGAR DOCX-to-HTM converter

Planned browser application for secure DOCX revision acceptance, PDF-first layout reconstruction, manual-derived EDGAR validation, all-page visual comparison and clean filing-asset ZIP download. Compliance and exact disclosure take priority; unresolved strict fidelity failures prevent download.

**Current delivery: Stage 1 architecture and analysis only. The application is not runnable.** See [project status](PROJECT_STATUS.md), [checkpoint](.agent-checkpoint.json) and [agent instructions](AGENTS.md). No conversion results or SEC acceptance are claimed.

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

Stage 2 will create backend configuration, upload/job APIs, storage and worker foundations. Stage 9 builds the UI; Stage 10 integrates the full pipeline; Stage 11 supplies deployment files. There are currently no server startup commands, environment settings or upload/download flows to run. Deployment, security and future environment configuration are specified in [deployment design](docs/deployment.md). Do not expose unfinished services as production-ready.

If inspection cannot import pypdf, use the analysis environment above. Missing fixtures must be located and verified, never replaced by fabricated test results. Read [decisions](docs/decisions.md) before changing a provider or compliance interpretation. Keep one stage per authorization; Git initialization, staging, committing, pushing and other Git writes are prohibited. Review and Git changes belong to the user.
