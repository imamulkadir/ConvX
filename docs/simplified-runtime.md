# Simplification Stage 2 — active runtime

The active application is one self-hosted Next.js Node server. Internal handlers directly start the existing Python converter in a bounded child process. FastAPI, Redis, Celery, SQLAlchemy/PostgreSQL, an account system and separate workers are not runtime dependencies. Their original source and user data are retained for recovery; they are not started or installed by current setup.

This stage changes architecture, not the document/rendering contract. The real existing DOCX revision/export/strict reference/SEC pipeline is retained. DOCX without required reference still blocks honestly. PDF input, the shared authoritative-input contract, Standard .html, revised EDGAR .htm and the minimal final page belong to the subsequent approved stages. A successful application startup is not a successful filing conversion.

## Setup and startup

From D:\Tools\ConvX, with Python 3.12 and Node 22.19 or later:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
cd apps/web
npm.cmd ci
cd ../..
.\.venv\Scripts\python dev.py
```

Use an existing .venv if already configured; do not overwrite or uninstall the user's packages unnecessarily. For tests install requirements-dev.txt, or the verified Windows/Python 3.12.10 requirements-dev-lock.txt. A clean test environment was installed without FastAPI/Celery/Redis/SQLAlchemy/psycopg and successfully imported/executed the converter.

Open the printed URL. There is no API token or Connect button. dev.py starts only Next, supplies its Python interpreter path, discovers a free loopback port and copies the local PDF.js worker. Next starts Python only when a document arrives. `npm.cmd run dev` in apps/web also works with the default root .venv. No schema initialization or dispatcher command is needed. The launcher ignores unrelated inherited Node preload hooks; no paid extension or service is a project dependency.

Optional settings go in apps/web/.env.local or the process environment: CONVX_PYTHON, CONVX_PROJECT_ROOT, CONVX_LIBREOFFICE_EXECUTABLE, CONVX_TEMP_ROOT. Defaults use this repository, .venv and the workspace's free LibreOffice where available. Existing root .env/database/artifacts are not edited or migrated implicitly. Missing renderer produces a real blocked diagnostic. Python itself and its packages must be installed.

`npm.cmd run build` / `npm.cmd run start` require a local Python installation and source/installed converter beside the app. This is a self-hosted Node deployment, not Edge or a serverless/standalone bundle containing Python. Dynamic Python/private filesystem paths are intentionally excluded from Turbopack dependency tracing; this avoids accidentally tracing the entire repository and its private state. Public deployment/access/rate controls and wider OS qualification remain later work.

## Request and process flow

The existing UI is a transitional adapter until Stage 8. It connects automatically to same-origin internal handlers and preserves useful progress, diagnostics, review and batch selection. Uploads now stream one document per raw-byte request with an encoded filename header; batch selection submits those requests sequentially. No new multipart dependency was added. There is no external API URL or service credential.

The POST handler verifies origin/loopback host, filename and transmitted byte count, and creates a new opaque UUID directory under var/conversions. A small atomic meta.json/request.json records upload/processing state. Existing var/artifacts and old databases remain untouched and are not exposed by the new routes. Only known opaque job references are served; there is no public job-list or arbitrary filesystem-path endpoint.

Next runs one conversion at a time with at most ten pending/admitting requests, starts Python through fixed argv with shell disabled, and records actual result/exit status. The Python supervisor uses the existing process monitor to bound elapsed time, RSS, output and artifacts, and checks cancellation. Converter admission now owns bounded ZIP/XML/macro/external-relationship validation independent of API Settings/Problem. The retained API file is only an optional historical adapter. converter.cli likewise no longer imports app.

Private progress/result files contain actual stages and diagnostics. Interrupted nonterminal jobs from another server instance become failed, never falsely completed or silently replayed. Explicit retries create a separate attempt workspace, preserve the original upload and enforce an attempt cap. A cancellation marker revokes access immediately and causes the Python supervisor to stop descendants. Node exit writes cancellation markers for its active jobs; the resource deadline is the fallback. Multiple self-hosted Node instances sharing storage are not supported by this small in-process scheduler.

## Limits, privacy and cleanup

Current product budgets are 20 MiB per document, ten pending uploads/conversions, one active conversion, 100 retained UUID directories, a 120-second upload deadline, roughly 320 seconds conversion time, 1.5 GiB supervised process-tree RSS and 512 MiB artifacts per process workspace. Original converter substage limits also apply. These are application limits, not SEC rules. The archive-audit subprocess has a separate bounded timeout/output limit. Large-source/archive snapshots use bounded memory; deployment-enforced CPU/filesystem/network sandboxing remains unqualified.

Temporary data expires after 24 hours. Periodic and admission-time cleanup removes only recognized expired/deleted resolved UUID children of the private runtime root, never linked/unknown directories or source fixtures. Upload rollback closes files and removes its own newly created directory. An initial upload manifest permits interrupted uploads to expire. Unknown/corrupt directories are preserved for safe operator review and can count toward the retained-directory cap.

Requests use private/no-store/nosniff headers. Cross-origin writes and writes using non-loopback hosts are rejected. There is no account system; unguessable conversion IDs are local capability references and must not be shared unintentionally. Use loopback binding. Diagnostic previews validate current source/PDF hashes and safe relative paths; HTM is a declared generated PNG capture, never active untrusted markup. Downloads capture ZIP bytes and invoke framework-free Python revalidation of complete evidence, actual files, archive manifest/CRC/SEC checks before serving.

The current legacy engine has no demonstrated successful qualified whole-chain ZIP. Positive archive mechanics and negative gate checks are real; the high-level success/download branch remains unqualified. Neither a PDF preview nor a process exit without matching proof permits a filing-ready claim.

## Testing and preserved history

The active pytest suite now targets converter unit/runtime/native/visual/regression checks. Service-specific unit tests were moved to tests/legacy, and original mixed integration files were copied there before retaining their converter cases. The old service-only integration modules remain historical opt-in tests and need their old dependencies/PYTHONPATH; they are not evidence for the new runtime. Package-security cases were adapted to the pure converter and retained in tests/runtime/test_admission.py. Root fixtures import old service packages lazily only if an old fixture is explicitly requested.

Node tests run real Python admission and cover byte budgets/rollback, origin/filename/path guards, cancellation, interruption and expiry. Browser tests start only a production Next server and use the clean Python environment for real native DOCX processing, honest reference failure, PDF canvas review, invalid-input rejection and accessible light/dark views. No mocked conversion engine, external processing API or fabricated success is used. See [test history](test-history.md) and [current status](../PROJECT_STATUS.md).

Stage 3 must deliberately replace the routine external Word-reference gate with the revised generated/uploaded-PDF authority contract. Keep Word-reference comparisons as regression evidence. Do not promote inspection/self-comparison into legacy passing proof. Mode-specific rendering/validation/ZIP changes remain their own stages.
