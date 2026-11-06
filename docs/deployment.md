# Local deployment and operational limits

The supported setup is one self-hosted loopback Next.js server with local Python, free LibreOffice and pinned Chromium installed. See [setup](simplified-runtime.md). `python dev.py` is the local development entry; `npm.cmd run build` and `npm.cmd run start` in apps/web use the same installed local converter. Node22.19+ and Python3.12+ are required. No premium conversion license or separate API/broker/database/worker service is required.

This is a self-hosted Node/filesystem application, not Edge or a serverless bundle containing Python. Supply local Python/converter/source and native dependencies beside the app. Private temp storage is outside public assets, defaults to var/conversions, and should reside on a private local filesystem. Preserve user's existing .env/data; optional current settings belong in apps/web/.env.local or the launcher process environment. Root .env.example does not automatically configure Next.

## Boundaries verified locally

Loopback host/same-origin mutation checks, opaque UUID ownership, bounded raw uploads, signature/ZIP/XML/macro/PDF action validation, path/symlink checks, private atomic state, timeout/RSS/output/disk monitoring, cancellation/retention cleanup and fresh proof-bound downloads are integrated. One conversion and one download audit can run concurrently; admission/pending jobs are capped at10, retained recognized jobs at100, uploads at20MiB by default, and retention at24hours. No account system is added for local use. IDs grant local document access and should remain private.

Default native supervisor budget is320seconds, combined monitored RSS1.5GiB and job artifacts512MiB; nested operations have tighter limits. Polling cannot preempt every native allocation or parser stall. Existing process isolation is application-level monitoring, not a complete operating-system hostile-document sandbox. Browser resources are restricted and proxies removed from native children, but that is not a universal OS network isolation guarantee.

## Public hosting

Public multi-user deployment has not been qualified. Do not expose the loopback application directly. A deliberate public deployment would need access controls, TLS, request/rate quotas, tenant isolation and enforced OS CPU/memory/disk/process/network isolation, retention/storage review and platform qualification. No production cloud deployment or SEC submission is claimed. Avoid logging document contents, credentials or local paths. Keep actual uploaded sources local unless the user explicitly authorizes a different configuration.

The earlier multi-service deployment plan is [historical](history/pre-stage10-deployment.md.txt). Current [security/dependency/performance review](stage10-review.md), [limits](limitations.md) and [test history](test-history.md) distinguish implementation from remaining operational limitations.
