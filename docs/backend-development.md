# Local processing development

The active application has no separately running backend. From the configured root environment run:

```powershell
.\.venv\Scripts\python dev.py
```

Open the printed URL, choose DOCX/PDF, optionally check SEC EDGAR Compliance, Convert to HTM and Download ZIP. The launcher starts one loopback Next server and supplies its Python interpreter. Update code and restart the launcher as needed. No API access token, uvicorn, Redis/Celery, database or worker startup is required.

One-time setup and optional local LibreOffice/Python/temp settings are in [current runtime](simplified-runtime.md). For an existing configured environment, do not recreate the environment or overwrite user configuration. The root .env.example is informational; Next reads apps/web/.env.local or process variables. Missing native dependencies produce understandable diagnostics rather than fake successful downloads.

For tests, install requirements-dev.txt in a configured Python environment, run `python -m pytest`, and run `npm.cmd test` / `npm.cmd run test:ui` in apps/web. UI tests build and launch their own production server. [Integration tests](integration-testing.md) verify real saved archives; [Stage10 review](stage10-review.md) records final scope and limitations. Retired service operation is preserved only in [historical notes](history/pre-stage10-backend-development.md.txt); do not use those commands for the active app.
