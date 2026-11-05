# MASTER EXECUTION PROMPT

**Before implementing any changes, every AI agent must read `AGENTS.md`, `PROJECT_STATUS.md`, and `.agent-checkpoint.json` and inspect the current repository state.**

Current workflow: the simplification refactor in this file replaces the earlier SEC-only development plan. See [Stage 1 audit](docs/refactor-audit.md), [decisions](docs/decisions.md) and [test history](docs/test-history.md). Root progress records track the revised stages; [historical status](docs/history/pre-refactor-status.txt) and [historical checkpoint](docs/history/pre-refactor-checkpoint.json) preserve the prior implementation. On resume, follow the current checkpoint and approval gate; the initial "Begin Stage 1" directives below do not authorize repeating a completed audit or starting Stage 2. Standard mode generates `.html`; EDGAR mode generates `.htm`.

# Refactor the Existing Application into a Simple, High-Fidelity DOCX/PDF-to-HTM Web Converter

## 0. ROLE AND OBJECTIVE

Act as a Principal Software Engineer, Senior Full-Stack Developer, Document Rendering Engineer, and SEC EDGAR Compliance Specialist.

Your task is to **refactor the existing project into a simple, lightweight, fully functional web application that converts DOCX and PDF files into high-fidelity HTM documents**.

The existing implementation became unnecessarily complicated, introducing separate backend services, API connections, queues, workers, infrastructure dependencies, and functionality beyond the actual requirements.

Simplify it.

Do not create a new project. Work within the existing repository, preserving useful functionality and removing unnecessary complexity.

The application must do one thing exceptionally well:

**Upload a DOCX or PDF, optionally enable SEC EDGAR compliance, convert it into an HTM file that preserves its original formatting as accurately as possible, and download a ZIP containing the HTM and its required assets.**

This must be an actual working conversion application, not a prototype, mockup, or demonstration.

Do not substitute placeholder implementations for real conversion functionality.

---

# 1. CORE USER EXPERIENCE

The entire application should have one simple workflow:

1. Open the web application.
2. Upload a `.docx` or `.pdf` file.
3. Optionally check **SEC EDGAR Compliance**.
4. Click **Convert to HTM**.
5. The application processes the document.
6. The application generates a high-fidelity `.html` file in Standard Mode or `.htm` in EDGAR Mode.
7. Required assets are extracted and prepared.
8. The application generates a ZIP file.
9. The user downloads the ZIP.

There must be no requirement for the user to:

- Configure API connections.
- Start a separate backend server manually.
- Configure Redis or Celery.
- Set up a database.
- Configure external conversion services.
- Manage processing workers.
- Configure document-specific conversion settings.
- Perform technical steps before every conversion.

The application should work through a single web interface and a straightforward local startup process.

A small amount of internal server-side processing is acceptable and necessary.

However, the user must not need to understand or manage that processing.

---

# 2. SUPPORTED INPUT FORMATS

The application must accept:

- Microsoft Word `.docx`
- Portable Document Format `.pdf`

Both input formats must support both conversion modes.

## DOCX Processing

When a DOCX is uploaded:

1. Validate the DOCX.
2. Detect tracked changes.
3. Accept all tracked changes automatically.
4. Preserve the resulting final document content.
5. Convert the accepted DOCX to PDF internally.
6. Use the generated PDF as the authoritative visual reference.
7. Analyze the PDF layout.
8. Generate HTM according to the selected conversion mode.
9. Extract required assets.
10. Validate and package the output.

Never change the uploaded original DOCX.

## PDF Processing

When a PDF is uploaded:

1. Validate the PDF.
2. Inspect its page dimensions and structure.
3. Extract its text, fonts, images, tables, and layout information.
4. Generate HTM directly from the PDF.
5. Extract required assets.
6. Validate and package the output.

**Do not convert uploaded PDFs into DOCX first.**

Use the uploaded PDF directly as the visual reference.

## Scanned PDFs

Detect scanned or image-only PDFs.

Where practical, use OCR to recover text and reading order.

Preserve the original appearance as closely as possible.

Do not fabricate uncertain OCR content.

Report OCR limitations when the extracted text cannot be verified reliably.

---

# 3. TWO CONVERSION MODES

The application must have one checkbox:

**SEC EDGAR Compliance**

It must be **unchecked by default**.

This checkbox determines which HTML generation strategy is used.

## MODE A — STANDARD HTM

### Condition

SEC EDGAR Compliance is unchecked.

### Objective

Generate a modern HTML5 document with maximum possible visual fidelity to the uploaded PDF or the PDF generated from the uploaded DOCX.

There are no SEC-specific HTML restrictions in this mode.

Use appropriate modern HTML and CSS features to preserve document formatting.

Supported techniques may include:

- HTML5 elements
- CSS3
- Embedded stylesheets
- Inline styles
- Flexbox
- CSS Grid
- Absolute positioning
- CSS transforms
- Modern table styling
- Precise font sizing
- Custom font embedding when legally permitted
- Page-sized containers
- Precise image positioning
- Modern image formats
- Advanced text spacing
- Print-specific styling

Use whichever combination provides the best visual accuracy.

### Formatting Preservation

Preserve the original document's:

- Fonts
- Font sizes
- Font weights
- Bold
- Italics
- Underlines
- Text colors
- Highlighting
- Paragraph spacing
- Line spacing
- Margins
- Indentation
- Alignment
- Tables
- Merged cells
- Table borders
- Table backgrounds
- Images
- Logos
- Headers
- Footers
- Page numbers
- Footnotes
- Endnotes
- Mathematical expressions
- Superscripts
- Subscripts
- Special characters
- Multi-column layouts
- Text boxes
- Vertical text
- Rotated elements
- Page dimensions
- Page boundaries
- Page breaks

The visual target is **pixel-perfect reproduction of the source PDF**.

However, do not falsely claim exact pixel equivalence when the rendering differs.

Text should remain selectable and searchable wherever technically possible.

Do not convert entire document pages into screenshots simply to achieve an identical-looking result.

### Standard Mode Assets

Allow:

- JPG
- JPEG
- PNG
- GIF
- SVG
- WebP
- Locally referenced fonts where necessary and legally permitted

Embed CSS directly inside the HTM.

Do not generate separate CSS files unless there is a compelling reason and the user explicitly approves changing the output requirements.

Avoid JavaScript dependencies for static document rendering.

The Standard Mode output extension is `.html`. EDGAR Mode uses `.htm`.

---

## MODE B — SEC EDGAR-COMPLIANT HTM

### Condition

SEC EDGAR Compliance is checked.

### Objective

Generate an HTM document using only the markup, attributes, character encoding, graphics, hyperlinks, and formatting techniques permitted by the SEC EDGAR Filer Manual.

### Reference Manual

Use:

`edgarfm-vol2-v78.pdf`

EDGAR Filer Manual, Volume II, Version 78, dated September 14, 2026.

Pay particular attention to:

- Section 5.1 — Constructing Attached Documents
- Section 5.1.1 — File Naming Standards
- Section 5.2.2 — HTML
- Section 5.2.3 — PDF
- Relevant EDGAR document-validation requirements

Read the actual manual and implement its restrictions explicitly.

Do not assume modern browser-compatible HTML is automatically accepted by EDGAR.

### EDGAR Restrictions

Enforce applicable restrictions on:

- HTML tags
- HTML attributes
- Styling
- Image formats
- Image references
- Hyperlinks
- Character encoding
- Filename lengths
- Filename characters
- Document resources
- Unsupported embedded content

Do not include:

- JavaScript
- Unsupported HTML5 elements
- Unsupported CSS
- SVG
- External stylesheets
- Remote images
- External fonts
- Iframes
- Unsupported nested tables
- Unsupported embedded objects
- Unsupported hyperlink destinations

Use JPG/GIF graphics according to the applicable manual requirements.

All image references must resolve to local files in the ZIP.

### Formatting Requirements

Preserve the document's original appearance as closely as possible without violating SEC restrictions.

Do not intentionally change:

- Disclosure text
- Financial figures
- Paragraph formatting
- Table structures
- Text alignment
- Image placement
- Fonts
- Special characters
- Headers
- Footers

If exact appearance cannot be reproduced using permitted EDGAR markup, report the limitation.

Do not silently use prohibited HTML or unsupported styling.

**EDGAR compliance must not restrict the Standard HTM mode.**

The two conversion modes should share PDF analysis but use separate HTML generation strategies.

### Compliance Validation

Validate generated EDGAR HTM against the supplied manual.

Provide clear errors identifying unsupported elements, invalid attributes, broken image references, or other violations.

Do not claim SEC acceptance unless the filing has actually passed an authorized EDGAR test submission.

---

# 4. SIMPLIFIED CONVERSION PIPELINE

Implement a unified conversion engine.

```text
             Upload File
                 |
         +-------+-------+
         |               |
         v               v
       DOCX             PDF
         |               |
         v               |
   Accept Tracked        |
      Changes            |
         |               |
         v               |
   Generate PDF          |
         |               |
         +-------+-------+
                 |
                 v
          Analyze PDF
                 |
                 v
       Extract Document
       Layout and Assets
                 |
                 v
      SEC EDGAR Compliance?
                 |
         +-------+-------+
         |               |
        YES              NO
         |               |
         v               v
   EDGAR-Compatible   Modern HTML5
      HTM Renderer     HTM Renderer
         |               |
         +-------+-------+
                 |
                 v
         Validate Output
                 |
                 v
        Package HTM + Assets
                 |
                 v
          Download ZIP
```

Do not create separate conversion engines for DOCX and PDF.

The shared processing path starts at PDF analysis.

Use the accepted DOCX's OOXML only when necessary to recover semantic structures that PDF extraction cannot reliably preserve.

---

# 5. UNIVERSAL DOCUMENT SUPPORT

This must be a general-purpose document conversion engine.

Do not design or optimize conversion logic exclusively around the supplied Barclays document.

The uploaded reference documents are only regression fixtures.

The application must dynamically analyze each document regardless of:

- Filename
- Issuer
- Document length
- Page count
- Page size
- Orientation
- Font family
- Table structure
- Image placement
- Paragraph structure
- Document category

Support documents such as:

- Prospectuses
- Pricing supplements
- Financial reports
- Legal agreements
- Research documents
- Business documents
- Technical reports
- Image-heavy documents
- Documents containing complex tables
- Multi-column documents
- Landscape documents
- Mixed-orientation documents

Do not hardcode layout coordinates, font names, table widths, or other properties from a particular sample.

Do not claim support for every possible document structure without testing.

Unsupported cases must produce meaningful diagnostics rather than corrupted output.

---

# 6. SIMPLIFY THE EXISTING PROJECT

The application already exists.

**Refactor it instead of recreating it.**

First inspect the current codebase.

Identify:

- Existing working components
- Existing conversion logic
- Existing frontend components
- Existing PDF analysis code
- Existing HTML generation code
- Existing SEC validation rules
- Unused dependencies
- Unnecessary services
- Duplicated code
- Overengineered architecture

Preserve functionality that already works.

Remove unnecessary infrastructure where safe.

Candidates for removal include:

- Separate FastAPI service
- Redis
- Celery
- Distributed workers
- Message queues
- Unnecessary databases
- API gateways
- Complex job orchestration
- Unnecessary authentication infrastructure
- Excessive deployment configuration
- Redundant abstraction layers

Do not remove required features simply to make the repository smaller.

Do not introduce new infrastructure unless technically necessary.

## Preferred Architecture

Use:

- Next.js
- React JSX
- Tailwind CSS
- DaisyUI
- Lightweight server-side document processing
- Python for conversion where necessary
- PyMuPDF for PDF analysis
- Pillow for image processing
- lxml for HTML validation

Use additional dependencies only when justified by a demonstrated need.

A single Next.js application may invoke a bundled Python conversion process internally.

Avoid a separately running public Python API.

Keep the application simple enough to run locally without starting several independent services.

### Important Runtime Considerations

File conversion is a server-side operation.

Do not attempt to perform unsupported Word-processing operations entirely inside the browser.

Evaluate a suitable DOCX-to-PDF renderer.

Microsoft Word may provide superior compatibility for some DOCX documents, but unattended Office automation has support and operational limitations.

Choose a practical implementation that works in the intended runtime and document any unavoidable dependency.

Do not silently substitute an incompatible renderer when it introduces formatting changes.

---

# 7. DOCUMENT LAYOUT ANALYSIS

Use the PDF as the primary source of visual layout information.

Extract:

- Page dimensions
- Page orientation
- Text coordinates
- Text blocks
- Individual text spans
- Font families
- Font sizes
- Font colors
- Text baselines
- Paragraph relationships
- Line spacing
- Tables
- Table boundaries
- Images
- Vector graphics
- Headers
- Footers
- Page numbers
- Text rotation

Create a shared internal document model.

Example:

```text
Document
 ├── Pages
 │    ├── Geometry
 │    ├── Text
 │    ├── Tables
 │    ├── Images
 │    ├── Graphics
 │    ├── Headers
 │    └── Footers
 └── Assets
```

Both HTML renderers must consume the same analyzed document model.

Do not duplicate PDF parsing logic between modes.

Use modular code, but avoid unnecessary layers of abstraction.

---

# 8. HIGH-FIDELITY HTM GENERATION

Implement two renderers:

1. Standard HTML5 Renderer
2. SEC EDGAR Renderer

## Standard Renderer

Use modern browser features to reproduce PDF layout.

Use CSS positioning, page containers, precise dimensions, and typography when appropriate.

Prioritize:

- Text accuracy
- Font fidelity
- Text positioning
- Line wrapping
- Table geometry
- Image positioning
- Paragraph spacing
- Page appearance

Preserve selectable text.

Use embedded CSS.

Do not create unnecessary external resource files.

## EDGAR Renderer

Use only compliant markup.

Use a document-specific rendering strategy that respects the manual's supported formatting features.

Avoid unsupported CSS positioning or modern tags.

Preserve financial and legal text exactly.

If the layout cannot be reproduced without violating SEC restrictions, return a clear validation failure.

## Character Handling

Preserve:

- Currency symbols
- Mathematical symbols
- Registered trademarks
- Copyright symbols
- Dashes
- Quotation marks
- Superscripts
- Subscripts
- Special punctuation
- Financial notation

Do not replace legitimate characters with question marks or unsupported glyphs.

Use suitable HTML entities or character references when required.

---

# 9. IMAGE AND ASSET HANDLING

Extract images from the PDF.

Where possible, preserve the original embedded image data.

Avoid unnecessary recompression.

For Standard Mode, use supported modern browser formats.

For EDGAR Mode, generate only permitted SEC image formats.

All images must retain correct:

- Width
- Height
- Aspect ratio
- Placement
- Color appearance

Use deterministic asset names.

Example:

```text
image001.jpg
image002.png
image003.gif
```

EDGAR mode must not output unsupported image formats.

Do not convert ordinary text into images.

Do not include unused assets.

Every referenced asset must exist.

All assets must be located in the ZIP root directory.

---

# 10. OUTPUT ZIP REQUIREMENTS

This section is mandatory for both modes.

The ZIP filename must be derived from the uploaded filename.

Example:

Input:

```text
06749LWD4_prelim_prospectus_automated.docx
```

Output:

```text
06749LWD4_prelim_prospectus_automated.zip
```

For PDF:

Input:

```text
financial-report.pdf
```

Output:

```text
financial-report.zip
```

## ZIP Contents

Example for Standard Mode:

```text
financial-report.zip
│
├── financial-report.html
├── image001.png
├── image002.jpg
└── image003.svg
```

Example for EDGAR Mode:

```text
financial-report.zip
│
├── financial-report.htm
├── image001.jpg
└── image002.gif
```

The `.htm` filename must be SEC-compatible when EDGAR mode is enabled.

If the source filename is too long, shorten the internal HTM filename deterministically.

The external ZIP filename should retain the input basename.

## Strict ZIP Rules

The ZIP must contain only:

- Exactly one document: `.html` in Standard Mode or `.htm` in EDGAR Mode.
- Required local assets referenced by that HTM.

All contents must be in the ZIP root.

Do not include:

- DOCX
- PDF
- JSON
- CSS files
- JavaScript files
- Logs
- Screenshots
- Reports
- Temporary files
- Nested directories
- Unused assets

CSS in Standard Mode must be embedded in the HTM.

Validate the ZIP before allowing download.

---

# 11. USER INTERFACE

Keep the interface minimal.

Use a single primary page.

## Header

Title:

**DOCX & PDF to HTM Converter**

Subtitle:

_Convert Word and PDF documents into high-fidelity HTM with optional SEC EDGAR compliance._

## Upload Area

Provide:

- Drag-and-drop support
- File selection
- Accepted extensions: `.docx`, `.pdf`
- Selected filename
- File-size validation
- Clear selection option

## Compliance Checkbox

Label:

**SEC EDGAR Compliance**

Unchecked by default.

When unchecked, display:

**Standard Mode — Modern HTML5 and CSS for maximum formatting fidelity.**

When checked, display:

**EDGAR Mode — Uses only SEC-permitted HTML tags, attributes, and supported assets.**

## Convert Button

Label:

**Convert to HTM**

Disable when no valid file is selected.

## Processing Indicator

Use simple progress messages:

- Validating document
- Accepting tracked changes (DOCX only)
- Generating PDF (DOCX only)
- Analyzing PDF
- Generating HTM
- Processing assets
- Validating output
- Packaging ZIP

Do not introduce a complex dashboard.

## Download

On success, show:

**Download ZIP**

Display the output filename.

On failure, show an understandable error message.

## Design Requirements

- Modern, professional appearance
- Responsive layout
- Light and dark modes
- Tailwind CSS
- DaisyUI
- React JSX, not TypeScript
- Keyboard accessibility
- Clear loading states
- Minimal UI clutter

Remove unnecessary pages and features.

The application should feel like a focused conversion utility, not an enterprise document-management platform.

---

# 12. FORMATTING VERIFICATION

Visual accuracy is a core requirement.

Use the PDF as the visual reference.

In Standard Mode, maximize fidelity using modern HTML/CSS capabilities.

In EDGAR Mode, maximize fidelity within SEC restrictions.

Implement a practical verification process.

At minimum:

- Compare extracted text.
- Verify page dimensions.
- Check images.
- Check tables.
- Detect missing content.
- Detect major positioning errors.
- Verify HTM renders successfully.

Where practical, add automated screenshot comparison using Playwright.

Use pixel-level comparison for regression tests.

Do not introduce a complex visual-analysis service.

Keep validation integrated into the conversion engine.

Do not claim pixel-perfect success without evidence.

For EDGAR Mode, distinguish visual differences caused by SEC restrictions from conversion defects.

---

# 13. SIMPLIFIED BACKEND IMPLEMENTATION

Avoid unnecessary distributed infrastructure.

Use a straightforward conversion process that can be invoked by the existing web application.

Suggested implementation:

```text
Next.js Web Application
        |
        v
Internal Server-Side Conversion Handler
        |
        v
Python Conversion Engine
        |
        v
Generated ZIP
        |
        v
Browser Download
```

No separately running FastAPI service is required unless the current implementation demonstrates a compelling technical reason.

Do not use Redis or Celery.

Do not introduce a database solely for conversion state.

Use temporary directories for each conversion.

Ensure multiple conversion requests cannot overwrite one another's files.

Handle errors and cleanup correctly.

Do not block the frontend with synchronous UI operations.

A simple server-side job mechanism or streamed processing response is acceptable.

If conversions exceed request time limits, implement the smallest reliable solution rather than introducing distributed infrastructure prematurely.

---

# 14. SECURITY

Treat uploaded documents as untrusted.

Implement:

- File extension validation
- File signature validation
- Upload-size limits
- Safe temporary directories
- Path traversal protection
- Processing timeouts
- Memory safeguards
- Safe document parsing
- Secure file downloads
- Automatic temporary-file cleanup
- No macro execution
- No arbitrary code execution

Avoid logging document contents.

Do not send uploaded documents to third-party services without explicit configuration and user authorization.

Keep processing local to the deployed application by default.

Do not add an unnecessary user-account system for the initial application.

If the app is exposed publicly, document appropriate access controls and rate limits.

---

# 15. REFERENCE TEST FILES

Use these existing files when available:

- `edgarfm-vol2-v78.pdf`
- `06749LWD4_prelim_prospectus_automated.docx`
- `06749LWD4_prelim_prospectus_automated(1).docx`
- `06749LWD4_prelim_prospectus_automated(1).pdf`

The first is the SEC compliance reference.

The remaining files are conversion regression fixtures.

Use the accepted DOCX and its reference PDF to verify:

- Track changes acceptance
- PDF generation
- Document text preservation
- Page layout
- Tables
- Images
- Fonts
- Footnotes
- Formatting fidelity

Also test direct PDF upload using the reference PDF.

Test both conversion modes for DOCX and PDF input.

**Do not hardcode the converter to these files.**

Add independent regression fixtures with different layouts.

---

# 16. PERSISTENT AI AGENT PROGRESS TRACKING

This requirement must remain in the simplified application project.

The development process must survive:

- Lost chat context
- New conversations
- Agent switching
- Interrupted implementation
- Long development gaps

Do not depend on conversation history alone.

Maintain the following files.

## AGENTS.md

This is the permanent AI agent instruction file.

Include:

- Project purpose
- Architecture
- Technology stack
- Coding conventions
- Conversion requirements
- Standard and EDGAR mode behavior
- Git restrictions
- Stage execution workflow
- Context recovery instructions
- Testing requirements

Every AI agent must read `AGENTS.md` before making changes.

## PROJECT_STATUS.md

Maintain a human-readable record containing:

- Current stage
- Completed stages
- Current progress
- Implemented features
- Files changed
- Test results
- Known bugs
- Pending tasks
- Next stage
- Suggested commit message
- Last updated date

Update this file after every development stage.

## .agent-checkpoint.json

Maintain machine-readable progress.

Example:

```json
{
  "project": "docx-pdf-to-htm-converter",
  "schema_version": 1,
  "current_stage": 1,
  "stage_status": "not_started",
  "last_completed_stage": 0,
  "next_stage": 1,
  "awaiting_user_approval": false,
  "completed_stages": [],
  "pending_tasks": [],
  "known_issues": [],
  "last_test_results": [],
  "suggested_commit_message": null
}
```

Update the checkpoint whenever meaningful progress is made.

Keep it synchronized with `PROJECT_STATUS.md`.

## docs/decisions.md

Record important technical decisions and their reasoning.

## docs/test-history.md

Record:

- Test commands
- Results
- Failures
- Relevant environment details
- Stage associated with each test

Do not fabricate successful tests.

---

# 17. CONTEXT RECOVERY PROTOCOL

When starting a new conversation or resuming the project:

1. Read `AGENTS.md`.
2. Read `PROJECT_STATUS.md`.
3. Read `.agent-checkpoint.json`.
4. Read `docs/decisions.md`.
5. Read relevant test history.
6. Inspect the existing code.
7. Inspect read-only Git status if available.
8. Identify the current development stage.
9. Verify completed work.
10. Identify unfinished work.
11. Resume from the last verified checkpoint.

Do not restart the project unnecessarily.

Do not redo completed stages without reason.

If progress files conflict with actual code, trust verified implementation and test evidence.

If the previous stage is marked as awaiting user approval, stop until explicitly authorized.

Do not proceed automatically merely because the project state has been recovered.

---

# 18. STRICT GIT RESTRICTIONS

These restrictions override all other instructions.

**Never initialize a Git repository.**

**Never stage files.**

**Never commit.**

**Never push.**

**Never create or switch branches.**

**Never merge, rebase, reset, stash, or clean repository changes.**

Do not perform Git write operations through shell commands, IDEs, libraries, scripts, or APIs.

Prohibited examples:

```text
git init
git add
git commit
git push
git checkout
git switch
git merge
git rebase
git reset
git stash
git clean
```

Read-only Git commands are permitted:

```text
git status
git diff
git log
```

You may create, modify, refactor, and remove project application files as required by the authorized development stage.

Do not modify Git metadata or history.

After each stage, provide a suggested commit message as plain text.

The user will manually commit and push the changes.

---

# 19. STAGE-BY-STAGE REFACTORING PLAN

Follow this sequence.

**Implement one stage at a time.**

## Stage 1 — Existing Project Audit

- Inspect the current application.
- Read all persistent progress files.
- Identify unnecessary infrastructure.
- Identify reusable components.
- Compare existing behavior against the revised requirements.
- Document the simplification plan.
- Update progress-tracking files.

Do not begin refactoring beyond this stage.

## Stage 2 — Simplify Architecture

- Remove unnecessary services.
- Remove unused infrastructure.
- Consolidate conversion processing.
- Simplify configuration.
- Preserve functional code.
- Ensure the application still starts.
- Update dependencies and documentation.

## Stage 3 — DOCX and PDF Input Support

- Support both `.docx` and `.pdf` uploads.
- Implement input validation.
- Add DOCX tracked-change acceptance.
- Add DOCX-to-PDF conversion.
- Add direct PDF analysis.
- Unify both inputs into the shared pipeline.

## Stage 4 — PDF Layout Analysis

- Extract text and font information.
- Analyze page geometry.
- Identify tables.
- Extract images.
- Extract vector graphics.
- Build the shared layout model.
- Add tests.

## Stage 5 — Standard HTM Renderer

- Implement modern HTML5 output.
- Implement advanced CSS styling.
- Reconstruct PDF layouts.
- Preserve selectable text.
- Extract modern assets.
- Improve formatting fidelity.
- Test different document types.

## Stage 6 — SEC EDGAR Renderer

- Read the supplied EDGAR manual.
- Implement supported tags and attributes.
- Implement permitted styling.
- Implement JPG/GIF asset handling.
- Implement filename restrictions.
- Implement compliance validation.
- Test EDGAR output.

## Stage 7 — ZIP Packaging

- Derive ZIP filename from input.
- Generate `.html` in Standard Mode or `.htm` in EDGAR Mode.
- Include only referenced assets.
- Use root-level files.
- Validate ZIP contents.
- Support both modes.

## Stage 8 — Simplify Frontend

- Build the minimal upload interface.
- Support DOCX/PDF selection.
- Add EDGAR checkbox.
- Set checkbox to unchecked by default.
- Add Convert button.
- Add processing progress.
- Add download control.
- Remove unnecessary dashboard elements.

## Stage 9 — Full Integration Testing

Test:

- DOCX to Standard HTM
- DOCX to EDGAR HTM
- PDF to Standard HTM
- PDF to EDGAR HTM

Verify ZIP contents and conversion behavior.

Run regression tests against the supplied documents.

Fix discovered defects.

## Stage 10 — Final Cleanup and Optimization

- Remove dead code.
- Remove unused packages.
- Optimize conversion performance.
- Improve error handling.
- Verify security.
- Verify output structure.
- Update documentation.
- Run final tests.
- Record remaining limitations.

Do not add new enterprise infrastructure.

---

# 20. MANDATORY STAGE APPROVAL GATE

After completing each stage:

1. Finish the actual implementation.
2. Run relevant tests.
3. Fix stage-specific defects.
4. Update `PROJECT_STATUS.md`.
5. Update `.agent-checkpoint.json`.
6. Update test history.
7. Update architectural decisions where necessary.
8. Report completion.
9. Provide a suggested Git commit message.
10. Stop.

Do not proceed to the next stage without explicit user authorization.

The user will manually review, commit, and push the changes.

Do not interpret silence or successful tests as permission to continue.

If the user requests changes to the current stage, implement those changes without automatically advancing.

## Required Stage Report

Use this format:

### Stage [N] — [Stage Name]

**Status:** Completed / Blocked

**Changes Implemented**

- Actual changes made
- Files created or modified
- Important technical decisions

**Testing**

- Tests performed
- Passed tests
- Failed tests
- Known limitations

**Progress Tracking**

- Project status updated
- Checkpoint updated
- Test history updated

**Suggested Commit Message**

```text
refactor: simplify [stage description]
```

**Next Stage:** Stage [N+1] — [Stage Name]

**Action Required:** Review, commit, and push the changes manually, then explicitly instruct me to continue.

Stop execution after the report.

---

# 21. HANDLING BLOCKERS

If a stage cannot be completed:

1. Identify the blocker.
2. Explain its technical cause.
3. Preserve completed work.
4. Document the remaining tasks.
5. Update progress records.
6. Report available test results.
7. Provide a suggested commit message if appropriate.
8. Stop for user instructions.

Do not fabricate results.

Do not claim a stage is complete when major functionality remains broken.

Do not silently replace the intended implementation with a mock or placeholder.

---

# 22. DEFINITION OF DONE

The application is complete when:

- The web application starts with a simple setup.
- DOCX uploads work.
- PDF uploads work.
- Track changes are accepted for DOCX inputs.
- DOCX-to-PDF conversion works.
- Direct PDF processing works.
- Standard HTM mode works.
- SEC EDGAR mode works.
- The EDGAR checkbox is unchecked by default.
- Standard mode supports modern HTML5/CSS.
- EDGAR mode enforces the supplied manual's rules.
- Document text is preserved.
- Images are extracted correctly.
- Formatting fidelity is measured and improved.
- Standard Mode produces `.html`; EDGAR Mode produces `.htm`.
- ZIP filenames match input basenames.
- ZIP files contain only the HTM and referenced assets at the root.
- Conversion failures are reported accurately.
- The UI remains simple and responsive.
- Unnecessary services have been removed.
- Automated tests pass.
- Documentation is updated.
- Persistent progress tracking works.
- Any AI agent can resume the project from the checkpoint files.

Do not claim universal pixel-perfect conversion unless demonstrated by actual testing.

Do not claim SEC filing acceptance without authorized EDGAR test validation.

---

# 23. FINAL EXECUTION INSTRUCTIONS

You are working on an existing application.

Do not create another project.

Do not initialize Git.

Start by reading:

1. `AGENTS.md`
2. `PROJECT_STATUS.md`
3. `.agent-checkpoint.json`
4. `docs/decisions.md`
5. `docs/test-history.md`

Read whichever of these files exist.

Inspect the current application and determine what was already implemented.

Do not assume the previous architecture must be preserved.

Do not assume every existing component must be removed.

Evaluate each component based on whether it directly contributes to the simplified conversion workflow.

Begin with:

**Stage 1 — Existing Project Audit**

During this stage:

- Inspect the repository.
- Identify existing functionality.
- Identify unnecessary infrastructure.
- Identify reusable code.
- Compare current functionality against the new requirements.
- Create a practical refactoring plan.
- Update persistent progress files.
- Run relevant non-destructive checks.

Then report:

- Findings
- Proposed simplifications
- Files changed
- Tests/checks performed
- Updated progress
- Suggested commit message

**Stop after Stage 1.**

Wait for the user to review, commit, push, and explicitly authorize Stage 2.

## FINAL NON-NEGOTIABLE RULES

- Never initialize Git.
- Never stage files.
- Never commit.
- Never push.
- Never modify branches or Git history.
- Never automatically move to the next development stage.
- Never rely only on chat history for project progress.
- Never produce fake conversion results.
- Never hardcode conversion logic to the Barclays sample.
- Never sacrifice SEC compliance to imitate formatting.
- Never impose EDGAR restrictions on Standard Mode.
- Always support DOCX and PDF input.
- Generate `.html` for Standard Mode and `.htm` for EDGAR Mode.
- Always package only HTM and required assets in the ZIP root.
- Always track development progress in repository files.
- Always report a suggested commit message after each stage.
- Always wait for explicit user approval before continuing.

# MANDATORY UPDATE — MODE-DEPENDENT OUTPUT EXTENSIONS

Update the existing DOCX/PDF converter to generate different HTML file extensions depending on the SEC EDGAR Compliance checkbox.

## Standard Mode (Checkbox Unchecked — Default)

- Generate a `.html` file.
- Use modern HTML5 and CSS3.
- Preserve document formatting with maximum achievable visual fidelity.
- Allow modern image formats and locally referenced assets.
- Package the `.html` file and its referenced assets in the ZIP root directory.

Example:

```text
financial-report.zip
├── financial-report.html
├── image001.png
├── image002.jpg
└── image003.svg
```

## EDGAR Mode (Checkbox Checked)

- Generate a `.htm` file.
- Use only HTML tags, attributes, styling, and image formats permitted by the SEC EDGAR Filer Manual.
- Apply SEC-compliant filename restrictions.
- Package the `.htm` file and its referenced JPG/GIF assets in the ZIP root directory.

Example:

```text
financial-report.zip
├── financial-report.htm
├── image001.jpg
└── image002.gif
```

## Implementation Requirements

1. Determine the output extension dynamically from the checkbox value.
2. Do not generate `.htm` in Standard Mode.
3. Do not generate `.html` in EDGAR Mode.
4. Ensure all generated asset references resolve correctly.
5. Update the frontend labels, backend conversion logic, ZIP packaging, validators, and automated tests.
6. Remove all previous requirements stating that both modes must use `.htm`.
7. Preserve the original input basename for the ZIP filename.
8. Do not introduce additional services or infrastructure.
9. Update `AGENTS.md`, `PROJECT_STATUS.md`, and `.agent-checkpoint.json` to reflect the revised requirements.
10. Follow the existing stage-by-stage workflow. Do not initialize Git, stage, commit, or push. Report changes and a suggested commit message, then wait for explicit authorization before continuing.

**Begin Stage 1 now.**
