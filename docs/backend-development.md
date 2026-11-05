# Stage 2 backend operation

Stage 9 update: [frontend setup](frontend.md) describes the implemented browser workspace. Authenticated /conversions/session returns admission limits. The owned preview route serves bounded generated PDF/declared visual PNG diagnostic artifacts after current source/attempt and ownership/retention checks. Preview never grants a ZIP; active HTM is not served. Earlier unimplemented-UI statements below are historical.

The API, durable job store, private upload admission, dispatch outbox and Celery worker are implemented. Stage 3 extends the worker to revision acceptance and free LibreOffice PDF export/validation; see [document processing](docx-processing.md) for setup and current results. Earlier Stage 2 jobs stopped at `blocked / awaiting_conversion_engine`; owned resume now explicitly requeues those jobs when appropriate. Missing renderer/reference remains blocked; strict PDF differences fail; a passing PDF stops before the unimplemented layout engine. No job becomes SEC-ready or downloadable yet.

## Install and configure

Run from the repository root with Python 3.12 or later. Tested on Windows/Python 3.12.10. Create a virtual environment and install the pinned resolution, then the local API package:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r services/api/requirements-lock.txt
.\.venv\Scripts\python -m pip install --no-deps -e services/api
.\.venv\Scripts\python -m pip install --no-deps -e packages/converter
Copy-Item .env.example .env
.\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Put that generated secret in `.env` as `CONVX_API_TOKENS='{"your-account":"YOUR_GENERATED_SECRET"}'`. Tokens identify separate owners and must be distinct, at least 32 characters and kept private. Empty token configuration intentionally prevents startup. Never use test/example tokens. A local opt-out exists only with explicit `CONVX_AUTH_MODE=local`, development environment and loopback clients; production rejects it. Tokens are supplied by `Authorization: Bearer ...`, never URL parameters. CORS is disabled by default; use a same-origin authenticated reverse proxy when the frontend is introduced.

Initialize the schema explicitly (also provisions configured owner IDs); run again after adding an account:

```powershell
.\.venv\Scripts\python -m app.cli init-db
.\.venv\Scripts\python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

SQLite is for single-host development. Use `CONVX_DATABASE_URL=postgresql+psycopg://...` in production; production also requires token access and prohibits automatic schema creation. `init-db` creates schema version 1, checks the recorded version, and does not migrate incompatible schemas. Subsequent schema evolution must use explicit versioned migrations. The runtime refuses a missing/incompatible schema. Back up databases and artifacts together. SQL echo is disabled.

## Broker, dispatcher and independent workers

Provide a real Redis instance via `CONVX_REDIS_URL`. Redis persists transport, while the database is authoritative for jobs, events and pending enqueue operations. API uploads remain durable during broker outages. A separately running dispatcher publishes the outbox and performs cleanup; run exactly the following from the same project root/environment:

```text
python -m app.cli dispatch
python -m celery -A workers.worker:celery worker --queues convx.admission --concurrency 2 --loglevel WARNING
```

The two commands run in separate supervised processes. Shared database and private storage paths must resolve identically across the API, dispatcher and worker. Production Celery uses Linux prefork; the Windows tests use solo pools for task mechanics only. Celery's [Windows support boundary](https://docs.celeryq.dev/en/stable/faq.html#does-celery-support-windows) means a successful Windows test is not production worker qualification. Docker/WSL infrastructure and process/network sandbox deployment belong to Stage 11 and are not installed here.

Tasks use JSON messages containing only job IDs, late acknowledgement, one prefetched message per worker, bounded retries and time/memory process-recycling settings. See [Celery task/worker configuration](https://docs.celeryq.dev/en/stable/userguide/configuration.html) and [Redis visibility timeout](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html). Database leases and version predicates reject duplicate/stale work; the dispatcher requeues expired claims within an attempt cap. Enqueue retries back off to five minutes and terminate visibly after the configured attempt limit. Multiple dispatchers can race safely; a publish/DB-ack crash may redeliver, so task claims remain idempotent.

`python -m app.cli dispatch --once` performs one maintenance/dispatch pass for inspection. Keep the continuous dispatcher alive for retention, lease recovery and cleanup. It is not started inside the API. Worker heartbeats describe admission capability only. Readiness always returns 503 with `conversion_ready=false` at Stage 2; `foundation_ready` reports database/storage/broker/live admission-worker checks separately. Health reports process liveness only.

## API usage

Submit multipart fields named `files`; each input creates an independent job. Optionally set `Idempotency-Key` using 1–128 letters/digits/dots/underscores/hyphens. Mixed batches return 202 with admitted jobs and per-file errors. If none are valid, return 422. Malformed or excessive multipart parts return 400; authentication, aggregate limits, quota and storage outages return structured request errors. Repeated matching keys return current job views; conflicting payload metadata returns 409. Deleted jobs are not resurrected by replay.

Routes: POST `/api/v1/conversions`; GET and DELETE `/api/v1/conversions/{id}`; GET `/{id}/events`, `/{id}/validation`, `/{id}/preview`, `/{id}/download`. All document routes enforce ownership. Polling is supported; SSE returns an ordered bounded replay then `reconnect`/`retry: 2000`, supporting Last-Event-ID. Reconnect forces periodic authorization without long-held DB transactions. No progress percentage is invented.

Preview/download return 409 without an artifact; expired artifacts return 410 and deleted/unowned jobs return 404. No unvalidated file-serving path exists. Deletion immediately revokes reads and requests cancellation; Stage 2 admission has no external renderer process and checks the attempt before final state changes. Cleanup waits beyond an active lease before removing its source. Later renderer stages must add process-tree termination.

## Admission and storage controls

The ASGI body guard authenticates before multipart parsing, enforces declared and received aggregate bytes and a total body-read deadline. FastAPI/Starlette uses spooled upload files ([file handling](https://fastapi.tiangolo.com/tutorial/request-files/)); each file is copied in bounded chunks with an independent byte limit into a UUID workspace. Set OS `TMPDIR`/`TEMP` to a private, quota-controlled disk for multipart spools in deployed API processes. The system temporary directory on this development machine is user-owned; Windows ACL isolation is an operator responsibility.

Admission checks ZIP signatures/CRC, entries, expanded sizes, ratios, paths, duplication, encryption, link entries, XML depth/DTD/entity safety, main Word part/MIME identity, relationships, active fields, embedded objects/macros and altChunk. Validation deadlines are cooperative between bounded reads/parses; they are not an OS kill boundary. Parser/native code still needs the Stage 11 process sandbox. Source XML is never rewritten. MIME declarations are evaluated only against actual parts: unused OLE defaults in the regression fixture do not imply embedded content. Inert HTTP/HTTPS/mailto source hyperlinks are retained as data and never fetched; external templates/images/objects are rejected. Final EDGAR hyperlink rules are stricter and remain Stage 6 work.

File paths use canonical UUIDs, not client names. Per-file, per-request, per-batch, active-job and retained-source-byte quotas are configurable. Committed failed/cancelled files count against retained-byte quota until cleaned. Uncommitted concurrent upload staging is bounded per request but requires a global disk quota and reverse-proxy connection/rate limits in deployment. Do not claim this stage enforces fleet-wide disk quotas.

Files are fsynced and atomically renamed before the job/event/outbox transaction. Failed admission/transactions remove staged copies; crash orphans older than the grace period are swept. Originals in tests/fixtures are untouched. Storage is private; POSIX modes are owner-only where supported, and Windows deployments must restrict ACLs. Retention revokes access at query time, removes files with retryable cleanup, then purges expired job/event/outbox metadata. Idempotency responses expire at retention. No document contents, source names, secrets or raw database exceptions are intentionally logged. Use the documented disabled access logs and restrict infrastructure logs too.

## Verification and troubleshooting

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\ruff check services workers packages/converter tests tools/fetch_libreoffice.py
.\.venv\Scripts\ruff format --check services workers packages/converter tests tools/fetch_libreoffice.py
.\.venv\Scripts\python -m pip check
python tools/verify_stage1.py
```

Optional live-service tests require `CONVX_TEST_REDIS_URL` and `CONVX_TEST_DATABASE_URL`. Use disposable services; the Redis test uses an isolated random queue and PostgreSQL test creates/drops only its generated `convx_test_<uuid>` schema. These tests skip when their URLs are absent. The default suite tests SQLite persistence, API security, lifecycle races and real Celery serialization/delivery over an in-memory test transport. It does not certify Redis or PostgreSQL deployment.

Startup token error: populate private `.env` and run from root. Schema error: initialize v1 explicitly; do not delete an existing database as a repair shortcut. Jobs remain queued: inspect dispatcher and Redis. Earlier `awaiting_conversion_engine` jobs can use the owned `/resume` action. For `PDF_RENDERER_UNAVAILABLE`, configure an absolute free LibreOffice executable; for missing references or failed PDF fidelity, inspect [Stage 3 instructions](docx-processing.md) and do not bypass the gate. Readiness remains 503 until the complete pipeline exists. See [test history](test-history.md) and [limitations](limitations.md).

Stage 4: converter version 0.4.0 adds typed PDF layout extraction. New worker settings are documented in `.env.example`; layout JSON is private and ownership remains tied to the current attempt. Passing analysis reports `awaiting_htm_generation`; final downloads remain unavailable. See [layout analysis](pdf-layout-analysis.md) for the inspection CLI and limits.

Stage 5 converter version 0.5.0 is editable-installable and workers now generate private HTM candidates. CONVX_HTM_MAX_BYTES and CONVX_HTM_MAX_NODES configure candidate limits. Other GenerationPolicy bounds apply internally. Reports expose candidate metadata/diagnostics only through the existing owned validation workflow; raw HTM/assets are not served. Candidate success blocks at awaiting_sec_validation. See [HTM reconstruction](htm-reconstruction.md).

Stage 6 converter version 0.6.0 includes the runtime JSON registry in its wheel. Worker configuration adds CONVX_SEC_MAX_NODES, CONVX_SEC_MAX_ASSETS and CONVX_SEC_MAX_ASSET_BYTES. A current owned validation report includes asset_normalization and sec_validation; API fields distinguish local validation from strict context qualification. No artifact-serving/UI/download route was added. Confirmed local file success would block at awaiting_visual_validation; actual styled candidates currently fail unresolved permissions. See [SEC validation engine](sec-validation-engine.md).

Stage 7 converter 0.7.0 requires pinned Playwright/NumPy and a separately installed matching Chromium (`python -m playwright install chromium`). New visual timeout/RSS/pixel/evidence settings are in .env.example. Old VISUAL_ENGINE_NOT_AVAILABLE jobs may be explicitly resumed; no automatic replay occurs. Strict visual success still blocks at awaiting_packaging; no preview/download/UI route was added. See [visual validation](visual-validation.md).

Stage 8 converter 0.8.0 adds deterministic packaging and the owned download handler. Four CONVX_PACKAGE_MAX_* budgets are in .env.example. Worker original names survive private source.docx storage. CLI accepts paired --form-type and --encoded-submission-bytes for trusted actual whole-submission context; ordinary upload context is still unresolved and must not be invented. Current reference/SEC/screen failures prevent download. A frontend is not yet implemented. See [ZIP packaging](zip-packaging.md).
