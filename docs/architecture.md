# Active architecture

ConvX is one self-hosted Next.js application. React JSX, Tailwind and DaisyUI implement one upload/conversion/download page. Same-origin internal Node handlers invoke bounded local Python processes; the user starts only `python dev.py`.

```text
Browser -> Next.js -> bounded Python -> authoritative PDF/layout
                                      -> Standard HTML5 or EDGAR flow
                                      -> actual Chromium verification
                                      -> validated root-only ZIP
Browser <- freshly audited download <- Next.js
```

DOCX revisions are accepted into a separate copy and free LibreOffice exports the visual-reference PDF. Uploaded PDFs enter shared analysis directly. PyMuPDF extracts source-bound geometry/text/assets once; separate renderers consume that model. Pillow handles graphic formats, lxml validates actual markup, NumPy compares raw pixels, Playwright/Chromium verifies actual rendering, and psutil bounds native descendants. No paid renderer, external conversion service, separate Python API, Redis/Celery, database or account system is installed by current requirements.

Opaque per-job directories contain atomic metadata, immutable input, private attempts and proof. One conversion runs at a time; admission/pending work is capped at10, retained recognized jobs at100, and one download audit can run at a time. Fresh proof is checked on every allowed download; no result cache bypasses source/asset/capture/ZIP validation. Requests exceeding the download bound receive retryable429 DOWNLOAD_BUSY.

Standard uses embedded CSS and selectable native SVG text/graphics; it does not rasterize ordinary text or impose EDGAR restrictions. EDGAR uses restricted normal-flow markup and local JPG/GIF under its separately hashed local interpretation. Neither model inspection nor local EDGAR checks grant legacy strict proof or SEC acceptance.

See [runtime/setup](simplified-runtime.md), [shared layout](shared-layout.md), [Standard](standard-renderer.md), [EDGAR](edgar-renderer.md), [ZIP](zip-packaging.md), [integration checks](integration-testing.md), [deployment](deployment.md) and [limitations](limitations.md). Retired service sources remain for historical recovery and legacy proof regressions; they are not the active runtime. Earlier architecture is retained in [history](history/pre-stage10-architecture.md.txt).
