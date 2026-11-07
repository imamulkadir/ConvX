# Minimal interface - revised Stage 8

The primary page is now a focused single-document converter. It uses the existing Next.js, React JSX, Tailwind and DaisyUI application, internal processing and fresh ZIP download audit. No token, connection setup, second server or new dependency is introduced.

## Workflow

1. Start `python dev.py` in the configured environment and open its printed URL.
2. Choose or drop one DOCX/PDF, up to the automatically loaded upload limit (normally 20 MiB). The page shows its name/size and a clear-selection control. Empty, unsupported, oversize and multi-file selections have understandable errors.
3. Optionally check **SEC EDGAR Compliance**. It is unchecked by default and displays the specified mode description. The selected mode is sent with the real upload, stored by the runtime and restored with a recovered conversion.
4. Click **Convert to HTM**. The UI shows actual upload progress and engine-stage messages, with no invented conversion percentage. File/mode controls lock while a conversion is active. Cancel upload/conversion is available.
5. On success, see the source-basename ZIP filename and **Download ZIP**. This uses the existing freshly audited real download. Choose **Convert another document** to remove this temporary conversion and reset the form.

The title/subtitle and mode descriptions follow AGENTS.md. Standard stays `.html`, EDGAR `.htm`. The existing renderer's limits are not changed by the interface. An unsupported EDGAR layout gives a clear failure and Standard suggestion, without a misleading download.

## Result review and recovery

Warnings have a compact **Conversion notes** disclosure: local fonts, LibreOffice compatibility, measured appearance differences and OCR limits remain visible on request. EDGAR success explicitly says local checks do not confirm SEC filing acceptance. No pixel-perfect claim is added.

**Preview and compare** is collapsed until requested. It retains the actual source PDF canvas, converted PNG, side-by-side/overlay/difference captures, page and zoom controls through existing safe preview routes. Capture DPI is now passed to the image component, fixing the prior missing-prop width calculation. This optional review does not expose active generated HTML or private intermediate files.

The page stores only the current opaque conversion ID in tab storage, not document contents. It migrates the newest old dashboard ID when present and tolerates damaged/unavailable optional browser storage. Reload restores active/completed state. Status polling retries connection interruptions; recovery retains the ID on transient request errors. Explicitly starting another document removes only that current temporary conversion. Old retained jobs are not promoted into qualified output.

The dashboard/sidebar/table/filter/help-tab workflows are removed. Diagnostic APIs and renderer validation remain intact; this is a simpler interface over the working converter, not a new project or replacement engine.

## Accessibility and presentation

Responsive light/dark layouts, remembered theme (with system preference fallback), native checkbox, keyboard file/clear controls, visible focus, skip link, live processing/results and alerts are included. Reduced-motion preference disables the spinner animation. No processing settings or technical proof fields are required in the primary workflow. Preview controls wrap and their canvases scroll within the page instead of forcing viewport overflow.

Production browser checks use real uploads, both modes and input types, actual ZIP save events, reference PDF/unsupported EDGAR cases, cancellation/recovery, drag/drop and a real browser network interruption. Four mobile/desktop light/dark captures and axe checks are recorded. No conversion or download is mocked. Read [test history](test-history.md), [current status](../PROJECT_STATUS.md) and [recovery notes](edgar-fix-resume.md) for actual final results.

Stage9 adds independent source/CRC verification of actual saved ZIPs; see [integration evidence](integration-testing.md). Stage10 cleanup/verification is complete; see [final review](stage10-review.md). No further stage is scheduled. Known complex EDGAR clipping, font/pixel, OCR and platform limits remain in [EDGAR](edgar-renderer.md), [Standard](standard-renderer.md) and [ZIP](zip-packaging.md) contracts.

Repaired complex EDGAR conversions display a prominent note when vertical sidebar text is shown horizontally. Conversion notes also identify retained clipped text, decoded legacy symbols and inactive forbidden external links. These are explicit layout/encoding limitations, not SEC acceptance or exact-pixel claims. See [repair details](edgar-rectangular-layout.md).
