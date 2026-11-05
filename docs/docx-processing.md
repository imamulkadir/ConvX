# Stage 3 document processing

All processing is local and uses free/open-source components. **No paid SDK, trial renderer, metered service or premium-license configuration is included.** The user's Stage 3 instruction supersedes the earlier Aspose candidate decision. LibreOffice is the only implemented renderer; `PDFProvider` is an interface for future free implementations, not an implicit provider switch.

## Installation and local reference run

Use the existing backend environment and install the independent converter package:

```powershell
.\.venv\Scripts\python -m pip install -r services/api/requirements-lock.txt
.\.venv\Scripts\python -m pip install --no-deps -e services/api
.\.venv\Scripts\python -m pip install --no-deps -e packages/converter
```

Install free LibreOffice using your OS package manager or a vendor distribution. This workspace has an administrative extraction of LibreOffice 26.8.2.2 at `.tools/libreoffice/program/soffice.com`; it does not require installing Office, contacting a paid conversion service or acquiring an SDK license. The vendor MSI was downloaded from its published mirror, size 375934976 bytes, SHA-256 `ff4b911403b67ee9e6249f820f9782c44bb32c94fdaa45b0da53a8e419e5307a`. [Vendor metadata](https://download.documentfoundation.org/libreoffice/stable/26.8.2/win/x86_64/LibreOffice_26.8.2_Win_x86-64.msi.mirrorlist) supplies the checksum. `tools/fetch_libreoffice.py` fetches/verifies the pinned Windows package; it does not install it or upload documents. Binaries and diagnostic workspaces are ignored by Git.

The extraction performed on this machine was `msiexec /a <verified-msi> /qn TARGETDIR=<workspace>/.tools/libreoffice`, with hidden UI and a private local log. A new extraction target is recommended; do not recursively remove an existing installation as a recovery shortcut. On Linux, supply the package-manager-installed `soffice` executable. Native Linux/prefork deployment remains untested here.

Run the supplied regression into a **new**, private directory:

```powershell
.\.venv\Scripts\python -m converter.cli tests/fixtures/06749LWD4_prelim_prospectus_automated.docx var/my-reference-check --libreoffice .tools/libreoffice/program/soffice.com --reference-pdf tests/fixtures/06749LWD4_prelim_prospectus_automated.pdf --expected-accepted-docx "tests/fixtures/06749LWD4_prelim_prospectus_automated (1).docx"
```

The CLI requires both installed local packages because its orchestration boundary applies the backend's complete upload admission policy before entering the converter. The converter processing modules themselves do not import FastAPI/Celery. It exits zero only for a passing configured PDF gate; nonpassing document processing exits nonzero (code 2, which Windows PowerShell may expose as command failure). A generated PDF is always exported from the newly accepted DOCX. The supplied PDF is used exclusively for comparison, never substituted as conversion output.

Current reference outcome: accepted text/table structure matches all 18 story parts, and the five input media parts are preserved byte-for-byte. LibreOffice produces 23 pages but **fails strict reference fidelity on every page**. This is an unsuccessful reference conversion, not a passing EDGAR filing. No HTML generation or ZIP is performed. See [reference qualification](stage3-regression.md).

## Revision acceptance contract

`converter.revisions.inventory.inventory` scans all Word XML parts, including main document, headers, footers, notes, textbox XML, styles and numbering. Supported Word namespaces include transitional and strict WordprocessingML. Detect known revisions, unknown `*Change` properties, conflict revisions and unsupported custom-XML/cell revisions. Refuse unsupported revision namespaces/types before creating accepted output.

`accept_revisions` operates on a copy and preserves current properties. It unwraps accepted insertions/move destinations, removes deleted text/move sources, removes historical property snapshots, accepts inserted paragraph marks, joins supported deleted paragraph marks, and accepts inserted/deleted table rows. It removes `trackRevisions` from settings, independently rescans the saved archive, checks source immutability and every original media-part hash, and writes a deterministic ZIP-based DOCX atomically. Unchanged package parts are byte-identical; no generic DOCX-to-HTML converter is used.

Paragraph joins require adjacent paragraphs in the same container without section-boundary ambiguity. The surviving paragraph mark retains its paragraph properties; disclosure runs are kept in order. Unpaired moved-content ranges, unsupported move contexts and invalid continuing vertical merges fail safely. Current property containers must match their revision snapshot type. Table cells, merges, row contents and images are never guessed into a new shape merely to finish a conversion.

Explicitly unsupported: `cellIns`, `cellDel`, `cellMerge`, custom-XML revision ranges, conflict revisions, moved paragraph-mark cases without a supported wrapper and ambiguous paragraph/section boundaries. Diagnostics identify code, part/XPath and remediation; originals remain unchanged. The tests cover core insertions/deletions/replacements, formatting, row revisions, simple paragraph joins, moved content and revisions in supported stories/textboxes. This does not claim comprehensive coverage of arbitrary OOXML extensions.

The selected strategy is deterministic OOXML acceptance plus native LibreOffice PDF rendering. It preserves source formatting/property bytes more directly than serializing every input through another word processor. It is deliberately narrower than claiming Word's native revision engine. Microsoft documents the [paragraph/property/row revision semantics](https://learn.microsoft.com/en-us/office/open-xml/word/how-to-accept-all-revisions-in-a-word-processing-document); unsupported structures remain explicit failures. No Word COM automation or python-docx revision assumptions are used.

## Renderer and resource controls

`LibreOfficeProvider` uses a fresh per-attempt profile, headless mode, fixed PDF export options, no document macros/Java runtime and private temp paths. Source admission forbids external templates/images/objects and active fields; inert hyperlinks are never fetched by application code. The child environment removes proxy variables. This is not a network sandbox: Stage 11 must enforce blocked outbound networking and private spool/disk/CPU policies at the OS/container boundary.

The process runner checks cancellation/deadlines, cumulative process RSS, diagnostic output size and generated-file bytes, and terminates its owned descendants. Linux uses a process group; Windows uses hidden processes and owned descendant tracking. Trusted console `soffice.com` is required on Windows so the launcher waits for rendering. This is not a general defense against malicious executable launchers or kernel/native-parser vulnerabilities. Configure only trusted renderer binaries; Stage 11 adds stronger deployment boundaries.

Record provider version, executable hash, all discovered system font-file hashes (combined fingerprint), exact PDF/source hashes, and comparison policy. Missing fonts/engine metric differences remain discrepancies, never silently approximated as a match. The first fixture run exceeded a 512 MiB RSS limit and failed safely; the current explicit default is 1 GiB, configurable, and the fixture rendered under that limit. No font sizes, table geometry or margins were altered to make the test pass.

## Intermediate PDF gate

`validate_pdf` rejects encrypted/unsafe PDFs, invalid page counts, bounded-file/object/page/raster violations and wholly unsearchable documents. Submitted unofficial-PDF SEC restrictions are separate from internal rendering safety; inert PDF hyperlink annotations are not executed. Compare all pages, including missing/extra pages, MediaBox/CropBox/rotation, extracted ordered words, word geometry, font-family/size/style/color character counts and exact RGB raster differences at controlled DPI. Record reading-order differences separately when extracted word inventories agree. Blank pages are supported when the document still contains selectable text elsewhere.

Geometry uses a recorded 0.01 pt tolerance; pixels must be exactly identical in this Stage 3 method. No blur, rescaling alignment, aggressive masking or antialiasing forgiveness conceals differences. This conservative method may reject harmless renderer differences, which is preferable to asserting pixel-perfect output without evidence. Stage 7 later implements richer discrepancy classification for HTM-vs-PDF; Stage 3 does not implement HTM rendering or the intermediate layout model.

Default strict mode requires a reference. Without one, the report says `PDF_REFERENCE_REQUIRED` and stops. A nonstrict development-only `pdf_require_reference=false` policy checks generation safety but **does not establish Word-layout fidelity**; production configuration rejects it. Do not disable the gate to label the supplied regression successful.

## Worker integration, diagnostics and resume

Configure `CONVX_LIBREOFFICE_EXECUTABLE` as an absolute path in `.env`; `.env.example` documents limits. The existing Celery admission task now validates source integrity, accepts revisions, renders and validates PDF sequentially. It persists `accepted.docx`, renderer output, per-page evidence and atomic `processing.json` under a private UUID attempt directory. Workers renew leases and poll cancellation; stale/deleted/expired attempts cannot advance stages or publish final state. No database schema change is required: the existing attempt ID owns the workspace.

`GET /api/v1/conversions/{id}/validation` returns the current authorized attempt's structured report, never raw document/PDF files. Preview/download remain gated. PDF success ends at `blocked / awaiting_pdf_analysis` with `LAYOUT_ENGINE_NOT_AVAILABLE`; missing renderer/reference is blocked; unsupported revisions or strict PDF differences fail. No conversion job becomes `completed` in Stage 3.

`POST /api/v1/conversions/{id}/resume` requeues owned, unexpired jobs blocked on earlier pipeline/renderer/reference capability, within the attempt cap. It does not resurrect deleted/failed jobs or reuse old attempt artifacts. Existing Stage 2 blocked jobs require this explicit action, not a mass automatic retry. Individual CLI reference paths are supported now; a browser reference-upload workflow remains for later integration. An authorized operator may provision `reference.pdf` in the job's private workspace before resume; there is no arbitrary API filesystem-path parameter. Never apply the Barclays reference globally to other uploads.

## Tests

Run `.venv/Scripts/python -m pytest -q`; native renderer tests use `.tools/libreoffice/program/soffice.com` here or `CONVX_TEST_LIBREOFFICE`. They skip explicitly if unavailable. A real one-page LibreOffice export compared to a separately generated baseline from that same renderer passes the strict gate. The 23-page Word baseline is a **negative qualification test**: automated success means the gate detects and reports its failure, not that its visual fidelity passed. Raw fixture PDFs are also self-compared across all 23 pages to verify a true identical-input pass and page-23 perturbations are detected. Tests use genuine document/PDF processing, not mock conversion output. See append-only [test history](test-history.md).
