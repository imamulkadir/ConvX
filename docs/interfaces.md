# Internal application interfaces

All routes are same-origin `/api/v1/conversions` handlers inside Next.js, using the Node runtime. No public Python API or token configuration is required. IDs are opaque local document-access capabilities and must remain private. Responses containing documents/state use no-store, nosniff and no-referrer headers.

| Request | Behavior |
| --- | --- |
| GET /session | Current upload limit and single-file selection limit; no auth configuration |
| POST / | Raw DOCX/PDF bytes; X-Convx-Filename is encoded display filename, X-Convx-Mode is standard or edgar (default standard) |
| GET /[id] | Actual job state/stage; no invented completion percentages |
| GET /[id]/validation | Actual processing diagnostics/proof summary, distinct local/legacy strict flags |
| GET /[id]/preview | Verified source/capture availability; optional kind/page selects PDF or PNG diagnostic bytes |
| GET /[id]/download | Current completed source/output/captures/ZIP are independently audited before response |
| DELETE /[id] | Cancel/revoke and clean recognized temporary state when no longer active |
| POST /[id]/resume | Bounded retry for supported missing-renderer/browser blocked states; not a way to bypass failed proof |

Upload and mutation handlers enforce loopback host and same-origin policy. Uploads stream under byte/deadline limits into UUID-owned paths; filenames never become private filesystem paths. Unsupported/unsafe names, including reserved device names, fail before conversion. Session limits describe the single-file interface, not an obsolete batch request or account mode.

One native download audit may run at a time; overlapping downloads return429 DOWNLOAD_BUSY and can be retried. Its slot is always released after success/failure. Every allowed request performs a fresh audit. Archive responses use source-basename filenames and safe UTF-8 Content-Disposition. Deleted/expired/changed files or evidence cannot grant a download.

Python accepts a bounded private request.json via fixed argv with no shell. Progress/result JSON remain private; only the qualified archive and verified diagnostic preview are served. Runtime report.stage=7 denotes the implemented packaging contract, independently of development Stage10. See [runtime](simplified-runtime.md), [ZIP contract](zip-packaging.md), [current review](stage10-review.md) and [historical interfaces](history/pre-stage10-interfaces.md.txt).
