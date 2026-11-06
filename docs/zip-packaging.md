# ZIP packaging - revised Stage 7

The current pipeline packages real Standard and EDGAR output after authoritative PDF analysis and actual browser verification. It uses the same local Next/Python runtime and no new dependency or service. Final stage status and approval gates are recorded in [project status](../PROJECT_STATUS.md) and [checkpoint](../.agent-checkpoint.json).

## Output contract

For `financial-report.pdf` or `.docx`, download `financial-report.zip`. Standard contains `financial-report.html`; EDGAR contains a deterministic SEC-compatible `.htm` name, shortened/sanitized with a source-name hash when needed. The ZIP download name preserves the original basename, including Unicode, spaces and apostrophes. Reserved/unsafe input basenames fail rather than creating dangerous archive paths.

Each archive contains exactly one mode-correct HTML document and its referenced local image assets, all at its root. No PDF, DOCX, JSON, CSS, JavaScript, log, report, screenshot, directory or unused asset is included. Standard's SVG is inside the HTML; current standalone image assets are JPG/PNG/GIF/WebP. EDGAR has only JPG/GIF assets. CSS stays embedded/inline.

The qualified private document keeps its existing name. Only its ZIP entry name changes, with **identical document bytes**. The archive validator checks all references under the final name before publication; an unresolved self-reference fails rather than rewriting disclosure. Actual offline opening of the renamed Unicode Standard document and the EDGAR document, text and image pixels are tested.

The writer reuses existing deterministic archive mechanics: HTM/HTML first, assets sorted, fixed timestamps/permissions, stored members, no encryption/ZIP64/extras/comments. UTF-8 member names are supported for Standard. Stored members deliberately avoid decompression-ratio hazards and simplify bounded byte/CRC checks; archives may be larger than a deflated ZIP. Limits: 128 MiB archive, 100 MiB combined payload, 64 MiB member, 1,001 members; current renderer limits may be lower.

## Current evidence contract

`packages/converter/packaging/current.py` has a separate typed `source-verified-mode-zip-v1` result. It binds source-PDF, generated HTML/assets and actual all-page browser evidence hashes, with mode and original/download/internal names. Page coverage, dimensions, text/geometry flags, raw measurements and EDGAR word-origin checks must be complete. Nonzero raw pixel differences remain visible warnings; no exact visual equivalence is inferred from a valid archive.

Actual archived bytes are reopened and every member CRC is read. The validator checks envelope/central-directory/local-header agreement, sizes, unique portable root names, member order, exact expected hashes and resolved references. It rejects appended data, duplicates/case collisions, unsafe paths, links/directories, compression/encryption and extra/unused members. Actual archived EDGAR bytes and JPG/GIF are revalidated under the documented [local EDGAR profile](edgar-renderer.md). Standard never invokes SEC validation.

This current contract does not satisfy or weaken the retired strict Word-reference/SEC package gates in `packaging/engine.py`. Those remain independently tested. A current EDGAR package can be downloadable while `strict_passed=false` and `sec_acceptance_confirmed=false`; download means that this converter's local output/package checks passed, not SEC filing acceptance or whole-submission qualification.

## Publication and download

Successful processing now ends as `packaged`, with `final_conversion_complete=true`; the internal Python process exits successfully and Next shows `completed` with download available. Existing warning diagnostics remain. Failure/cancellation/source-integrity checks prevent completion. Windows atomic-state publication retries transient sharing failures for at most one second; a launch/publication exception produces an explicit failed state instead of silently leaving a job running. Each request/attempt uses its own private directory; no archive can overwrite another job.

Every download runs a fresh bounded Python audit through the existing internal handler. It checks the request's mode/name/attempt against the report, current original source and authoritative PDF, current HTML/assets, persisted browser comparison and capture hashes, exact archive payloads and CRCs. Tampered/missing evidence or archives fail closed. Cancellation, expiration, deletion and changed job state/version prevent delivery. Next serves the already-buffered bytes only when their SHA and length match the fresh audit. Missing/unsafe/oversize archives return an understandable validation error.

Downloads use `application/zip`, no-store/nosniff headers and RFC5987 UTF-8 Content-Disposition with reserved punctuation escaped. Browser tests click Download ZIP and observe actual saved filenames and ZIP bytes through the production Next instance; no response is mocked.

## Limits retained

All three supplied complex fixtures continue to fail EDGAR clipping checks on page 1 and receive no successful EDGAR ZIP. Their Standard path is packageable. Independent real PDF and native DOCX cases exercise the supported EDGAR path. The local CSS/character interpretation, font/rasterization differences, OCR/platform limits and unsupported geometry remain as documented in the renderers. Packaging does not waive renderer failures.

The Stage 8 single-file interface and EDGAR checkbox now use this real download flow. Broader four-path integration qualification is Stage 9; final optimization/cleanup is Stage 10. Do not advance without explicit authorization. See [test history](test-history.md) and [decisions](decisions.md) for measured results and recovery details.

Previously retained PACKAGING_ENGINE_PENDING jobs are not automatically promoted; re-upload to run the new pipeline and create a qualified archive. Restart the local development server after updating runtime code.
