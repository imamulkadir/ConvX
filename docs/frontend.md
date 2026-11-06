# Converter interface

The primary page is a focused React JSX document converter with Tailwind/DaisyUI, responsive light/dark themes and keyboard accessibility. Start `python dev.py` from the configured root environment and open its printed URL.

Choose or drop one DOCX/PDF, leave SEC EDGAR Compliance unchecked for Standard `.html` or check it for supported restricted `.htm`, then Convert to HTM. Actual local progress/errors lead to an audited Download ZIP. The ZIP retains the uploaded basename. Optional notes and collapsed source/HTML/overlay/difference comparison expose real captures without technical setup or a dashboard. Reload recovers the current tab job; cancellation/reset revokes it.

No connection dialog, access token or separate backend is required. One-file limits are published by the internal session route; unused dashboard progress-index/retry lists are removed. Preview capture membership now uses a Set rather than repeated linear scans, preserving source/hash checks. Download concurrency is bounded and returns a retryable message when another audit is active.

See [interface details](simple-interface.md), [runtime](simplified-runtime.md), [integration checks](integration-testing.md) and [limitations](limitations.md). Real production browser checks exercise both inputs/modes, actual ZIP bytes, reference PDF, failure/cancel/recovery, themes and accessibility. Earlier dashboard design is [historical](history/pre-stage10-frontend.md.txt).
