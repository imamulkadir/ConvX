# One-command local development

From the repository root:

```powershell
.\.venv\Scripts\python dev.py
```

Open the workspace URL printed by the launcher, normally http://127.0.0.1:3000, and choose **Use local access**. No token, manual environment-variable setup or Redis service is required for this development command. First-time dependency installation still follows [backend setup](backend-development.md) and `npm.cmd ci` inside apps/web.

The launcher initializes the existing configured SQLite schema and starts three independent owned processes: the API, a real serial conversion worker, and the Next development server. The worker polls queued local-owner jobs from the database and invokes the actual existing admission/conversion pipeline. Atomic claims, attempt leases, cancellation, retention cleanup and every PDF/SEC/visual/package gate still apply. It records real outcomes and acknowledges the local outbox without sending to Redis. It does not simulate conversions or run them in API requests.

The command overrides access and execution mode only in its process environment. It does not edit your .env or credentials. Production/non-SQLite settings are rejected; all servers bind loopback. It processes only the local account's queued jobs. Default production operation remains Redis/Celery. Do not use this launcher for deployment.

Existing development servers are left alone. When a preferred port is occupied, the launcher chooses another and prints its exact URL. A separate ignored .next-local build directory avoids conflicting with another Next dev server. Ctrl+C stops this launcher's processes and their descendants. API code reload watches only backend/converter source; frontend hot reload remains enabled. Restart the launcher after changing worker code. `--no-reload`, `--api-port PORT` and `--web-port PORT` are optional controls.

The workspace's free LibreOffice executable is detected when no renderer is configured. It is not installed/downloaded by the launcher. Missing renderer, required reference or failed validation becomes a visible blocked/failed result. **This fixes jobs waiting for a missing worker; it does not resolve the existing reference, compliance or fidelity failures.**

For the previously stuck real upload, the new worker performed attempt 1, accepted revisions, generated PDF and then reported PDF_REFERENCE_REQUIRED. Waiting for a queue is fixed; providing/qualifying reference evidence is a separate processing requirement. No source or gate was altered to hide this failure.
