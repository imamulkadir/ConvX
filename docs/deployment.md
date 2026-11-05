# Deployment design

No deployment is runnable at Stage 1. Dockerfiles, Compose and reverse-proxy configuration belong to Stage 11; API/worker foundations belong to Stage 2.

Planned compatible services: Linux containers for Next.js, FastAPI, Celery, Redis, PostgreSQL and analysis/Chromium workers. Keep rendering in a separate restricted runtime chosen against the selected provider's supported platform and license. A licensed self-hosted SDK avoids sending confidential documents to third parties; a remote provider requires explicit data-handling approval and a documented contract.

Terminate TLS at the reverse proxy. Authenticate all document routes; apply owner isolation, upload quotas, request-body limits and rate limiting. Production refuses unauthenticated configuration. Local unauthenticated mode, if provided, binds loopback and is explicit. Use narrow CORS, CSRF protections where cookie authentication is used, and separate secrets for broker/database/storage. Never log document contents, tokens, URLs with credentials or client filesystem paths.

Stream upload bytes with a hard cap, not just a Content-Length check. Bound ZIP entry count, aggregate expanded bytes, per-entry size, compression ratio, XML depth and parse time. Reject traversal, absolute paths, duplicate members, symlinks, macros, embedded executable objects, external relationships and encrypted packages. Disable DTD/entity/network resolution. Source names are display metadata only; UUID storage paths must be contained within the workspace.

Workers need enforced CPU/memory/process/disk quotas, bounded concurrency, per-stage timeouts and whole-process-tree termination. Block renderer/browser outbound traffic at the network boundary. Preview HTML runs on an isolated origin in a sandbox with scripts and network blocked, with authenticated assets and restrictive CSP. Avoid serving untrusted HTM under the API's privileged origin. Health/readiness includes worker heartbeat and renderer capability; no false readiness if required components are absent.

Store disclosure artifacts privately, encrypt storage/backups, configure retention and cleanup retries, and audit access using opaque IDs. Keep upload, scratch, diagnostics and publication directories separate. Back up job state consistently with artifact references. Test cancellation/expiration races, failed cleanup, broker redelivery, worker death and restore behavior before production.

Stage 2 configuration should cover environment, access control, database/broker URLs, storage root, admission/expansion limits, timeouts, retention, concurrency and quota limits. Renderer/rule/browser/font profiles must be versioned. No real secrets belong in `.env.example`. Pin actual dependencies and build artifacts during implementation; architectural candidates are not installed application dependencies.
