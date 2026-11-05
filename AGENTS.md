# Agent recovery entrypoint — Stage 1

**Before implementing any changes, every AI agent must read `AGENTS.md`, `PROJECT_STATUS.md`, and `.agent-checkpoint.json` and inspect the current repository state.**

Then read [decisions](docs/decisions.md), [test history](docs/test-history.md), [architecture](docs/architecture.md), [interfaces](docs/interfaces.md), [pipeline](docs/conversion-pipeline.md), [SEC rules](docs/sec-compliance.md), [reference findings](docs/reference-findings.md) and [limitations](docs/limitations.md). Verify actual files and relevant tests before trusting recorded completion. Read-only Git inspection is allowed when available; all Git writes are prohibited.

The current directory is the project root; do not create a nested edgar-converter directory. Architecture documents define planned module paths and conventions: typed Python boundaries, JSX frontend, independent Next.js/FastAPI/Celery services, Redis transport, persistent job storage and private artifacts. PDF-first reconstruction, selectable disclosure, manual-derived compliance, strict fidelity failure and root-only HTM/JPG/GIF ZIPs are mandatory.

Implement only the authorized stage, verify it, update persistent records, report results and a suggested commit message, then stop. Explicit authorization is required before Stage 2. A commit report alone is not authorization. Resume partial work without overwriting unrelated files. Consult the current fixture inventory rather than inferring revision roles from filenames.

The original master instructions follow intact.

---

# MASTER EXECUTION PROMPT

# Build a Production-Ready SEC EDGAR DOCX-to-HTM Web Application

## 0. ROLE AND OPERATING MODE

Act as a Principal Software Architect, Senior Full-Stack Engineer, Python Backend Engineer, Document Rendering Specialist, Quality Assurance Engineer, and SEC EDGAR Filing Compliance Specialist.

Your responsibility is to design, implement, test, optimize, and document a complete web application that converts Microsoft Word DOCX documents into SEC EDGAR-compliant HTM documents while preserving their original formatting with the highest technically achievable visual accuracy.

This is a real software engineering project, not a demonstration.

**Build production-quality functionality. Do not create mock conversion engines, simulated results, or placeholder implementations.**

You must work sequentially, implement one development stage at a time, test your work, update persistent progress records, report completion, and stop.

The user is responsible for Git commits and pushes.

Never initialize a Git repository, stage files, commit, push, or automatically proceed to another development stage.

---

# 1. PROJECT OBJECTIVE

Build a browser-based application that allows users to upload one or multiple DOCX documents and automatically:

1. Validate the uploaded DOCX.
2. Accept all tracked changes.
3. Preserve the final accepted content and formatting.
4. Generate a PDF from the accepted DOCX.
5. Use the generated PDF as the authoritative visual layout reference.
6. Analyze the PDF's text, tables, fonts, images, coordinates, and page geometry.
7. Convert the PDF into an SEC EDGAR-compliant `.htm` document.
8. Extract and convert graphics into permitted SEC image formats.
9. Reconstruct the original PDF appearance with maximum possible fidelity.
10. Validate all HTML elements, attributes, image files, hyperlinks, and other applicable SEC requirements.
11. Render the generated HTM and compare it against the PDF.
12. Identify and attempt to resolve formatting discrepancies.
13. Generate a clean ZIP containing only the final `.htm` and referenced images.
14. Allow users to download the ZIP from the web application.

## Core Requirement

**The generated HTM must visually reproduce the intermediate PDF without intentional formatting changes.**

Preserve:

- Fonts and font sizes
- Bold, italic, and underline formatting
- Text colors
- Paragraph alignment
- Margins
- Indentation
- Line spacing
- Paragraph spacing
- Text wrapping
- Table dimensions
- Table borders
- Cell spacing
- Headers and footers
- Page numbering
- Images and logos
- Mathematical expressions
- Superscripts and subscripts
- Special characters
- Complex positioning
- Vertical or rotated text
- Multi-column layouts
- Page boundaries where technically reproducible

Do not arbitrarily change the source document's appearance to simplify conversion.

However, SEC compliance is mandatory. If exact visual reconstruction conflicts with permitted EDGAR markup, do not silently produce an invalid filing.

Record the incompatibility, report the discrepancy, and mark strict validation as failed.

## Success Priorities

1. SEC EDGAR compliance.
2. Exact preservation of filing content.
3. Maximum visual fidelity to the generated PDF.
4. Selectable and searchable disclosure text.
5. Reliable automated processing.
6. Security and document confidentiality.
7. Performance and scalability.
8. Maintainability.

Pixel-perfect appearance is the strict acceptance objective, not an assumption that every arbitrary document can satisfy.

---

# 2. REFERENCE MATERIALS

The project includes four reference files.

### SEC Filer Manual

`edgarfm-vol2-v78.pdf`

EDGAR Filer Manual, Volume II, Version 78, September 14, 2026.

This is the primary compliance reference.

Inspect all relevant requirements, particularly:

- Chapter 5 — Constructing Attached Documents and Document Types
- Section 5.1.1 — File Naming Standards
- Section 5.2.2 — HTML
- Section 5.2.3 — PDF
- Relevant graphics and hyperlink requirements
- Document-validation requirements
- Applicable submission restrictions

Use the manual's actual rules rather than assuming that ordinary modern browser HTML is SEC-compatible.

Create a versioned compliance rule registry with references to the relevant manual sections.

Do not invent SEC requirements.

Where the manual is ambiguous, document the uncertainty and implement conservative validation.

### Original DOCX

`06749LWD4_prelim_prospectus_automated.docx`

Contains tracked changes.

### Accepted DOCX

`06749LWD4_prelim_prospectus_automated(1).docx`

This document represents the expected result after accepting tracked changes.

### Reference PDF

`06749LWD4_prelim_prospectus_automated(1).pdf`

This 23-page PDF represents the accepted document's intended appearance.

Use these files as mandatory regression fixtures.

If the files are not in the project directory, locate them in the accessible working environment.

If unavailable, document the missing fixtures instead of fabricating test results.

Never modify the original reference files.

---

# 3. MANDATORY PROCESSING PIPELINE

Implement the following pipeline exactly in its logical order:

```text
DOCX Upload
    |
    v
DOCX Validation
    |
    v
Accept All Tracked Changes
    |
    v
Create Accepted DOCX
    |
    v
Convert Accepted DOCX to PDF
    |
    v
Validate PDF Generation
    |
    v
Analyze PDF Layout
    |
    v
Extract Text, Tables, Fonts,
Images, Graphics, and Coordinates
    |
    v
Build Intermediate Layout Model
    |
    v
Generate EDGAR-Compatible HTM
    |
    v
Extract and Normalize Image Assets
    |
    v
Validate SEC Compliance
    |
    v
Render HTM Using Chromium
    |
    v
Compare HTM Against PDF
    |
    v
Diagnose and Resolve Differences
    |
    v
Run Final Validation
    |
    v
Generate Clean ZIP
    |
    v
Download ZIP
```

Use the generated PDF as the authoritative visual layout source for HTM reconstruction.

You may additionally consult the accepted DOCX's OOXML structure to resolve:

- Text reading order
- Table relationships
- Merged cells
- Paragraph structure
- Hyperlinks
- Drawing relationships
- Headers and footers
- Footnotes
- Semantic ambiguities

Do not bypass PDF generation by substituting a generic DOCX-to-HTML converter.

The PDF-first workflow is mandatory.

Intermediate artifacts must remain outside the final ZIP.

---

# 4. APPLICATION TECHNOLOGY STACK

## Frontend

- Next.js with App Router
- React using JSX, not TypeScript
- Tailwind CSS
- DaisyUI
- Lucide icons

Use JavaScript and JSX throughout the frontend.

## Backend

- Python
- FastAPI
- Pydantic
- PyMuPDF
- Pillow
- lxml
- OpenCV where useful
- Playwright

## Processing Infrastructure

- Redis
- Celery
- Isolated conversion workers
- Persistent job-state storage
- Temporary artifact storage

## Packaging

- Python `zipfile`

## Deployment

- Docker for compatible services
- Separate document-rendering infrastructure
- Reverse proxy
- Environment-based configuration

Keep the frontend, backend API, and processing workers independent.

Do not perform resource-intensive conversions inside Next.js API routes.

Use asynchronous jobs with polling or server-sent events.

Do not assume Microsoft Office automation is supported for unattended production-server workloads. Investigate its support and licensing constraints, evaluate supported rendering alternatives, and document the selected implementation.

---

# 5. DOCUMENT PROCESSING ENGINE

## 5.1 Accept Tracked Changes

Support Word revisions including:

- Insertions
- Deletions
- Replacements
- Formatting changes
- Paragraph revisions
- Table revisions
- Moved content
- Revisions in headers and footers
- Revisions in supported text boxes and story ranges

Prefer Word-compatible native revision processing where a supported execution environment exists.

Do not assume `python-docx` can fully handle all revision types.

Verify that:

- Accepted text remains.
- Deleted text is removed.
- Formatting revisions are applied.
- Tables remain structurally intact.
- Embedded images remain intact.
- Unresolved tracked changes do not remain.
- The original DOCX is unchanged.

If unsupported revisions are encountered, fail safely and report them.

## 5.2 DOCX-to-PDF

Produce a PDF matching the accepted document's Word print layout as closely as possible.

Preserve:

- Paper size and orientation
- Sections
- Margins
- Page breaks
- Fonts
- Paragraph spacing
- Tables
- Borders
- Graphics
- Footers
- Page numbers
- Footnotes
- Rotated text
- Text boxes
- Special characters

Implement a pluggable rendering-provider interface.

Evaluate:

- Supported Microsoft Word-compatible rendering
- Commercial document-rendering services or libraries where appropriate
- LibreOffice as a fallback, subject to fidelity testing

Do not assume different rendering engines produce equivalent layouts.

Compare the generated PDF against the uploaded reference PDF.

Use page dimensions, page count, text positions, and rendered-page differences.

Do not proceed to HTM generation for a document whose PDF violates configured strict PDF validation.

---

# 6. PDF-TO-HTM CONVERSION ENGINE

This is the most important part of the application.

Do not use a generic PDF-to-HTML library as the entire implementation.

Build a modular reconstruction engine.

## 6.1 PDF Extraction

Extract:

- Page geometry
- Text blocks
- Text lines
- Individual spans
- Character coordinates where needed
- Font names
- Font sizes
- Font weights
- Italic and underline properties where recoverable
- Text colors
- Bounding boxes
- Text baselines
- Line heights
- Paragraph relationships
- Tables
- Cell boundaries
- Borders
- Images
- Vector drawings
- Headers
- Footers
- Page numbers
- Text rotation
- White-space information

Use PyMuPDF and other specialized libraries where justified.

## 6.2 Intermediate Layout Model

Create a structured document model independent of the final HTM generator.

Suggested structure:

```text
Document
  ├── Metadata
  ├── Pages
  │    ├── Geometry
  │    ├── Text Blocks
  │    │    ├── Paragraphs
  │    │    ├── Lines
  │    │    └── Text Spans
  │    ├── Tables
  │    ├── Images
  │    ├── Vector Elements
  │    ├── Headers
  │    └── Footers
  └── Assets
```

Maintain deterministic conversion behavior.

Do not introduce Barclays-specific logic into the general-purpose engine.

## 6.3 HTM Reconstruction

Generate `.htm` using only permitted EDGAR HTML constructs.

Preserve the PDF's appearance as precisely as possible.

Handle:

- Paragraph alignment
- Text positioning
- Font size
- Font weight
- Font style
- Spacing
- Indentation
- Tables
- Borders
- Merged cells
- Financial data
- Footnotes
- Page numbers
- Vertical text
- Images
- Mathematical expressions
- Complex prospectus layouts

Use the permitted HTML attributes and inline formatting capabilities defined in the manual.

Do not assume CSS positioning, external stylesheets, or arbitrary HTML5 elements are supported.

Where exact rendering cannot be achieved using allowed constructs, record an explicit fidelity failure.

Ordinary disclosure text must remain selectable and searchable.

Do not convert entire PDF pages into images merely to produce visual similarity.

---

# 7. SEC COMPLIANCE ENGINE

Build a dedicated, versioned compliance validator based on the supplied EDGAR manual.

Create an explicit registry of:

- Permitted HTML tags
- Permitted attributes
- Restricted attributes
- Prohibited elements
- Character-encoding rules
- Hyperlink restrictions
- Image-format restrictions
- Local asset references
- Filename requirements
- Applicable document limits
- PDF restrictions where relevant

Validate the actual generated files, not just the intermediate layout model.

Reject unsupported constructs such as:

- JavaScript
- Script elements
- Event handlers
- Unsupported HTML elements
- Unsupported CSS
- SVG
- Iframes
- External fonts
- Remote images
- Unsupported data URIs
- Invalid links
- Unsupported nested tables
- Prohibited embedded objects

Apply the actual manual rules rather than a generic blanket HTML policy.

Ensure special characters are encoded correctly.

Preserve disclosure text without changing its meaning.

For failed validation, provide:

- Error code
- Description
- Affected file
- Affected element
- Relevant manual section
- Suggested remediation

Local validation is not proof of SEC acceptance.

Where available, document how to perform authorized EDGAR test submissions.

---

# 8. IMAGE AND ASSET ENGINE

Extract and normalize graphics from the PDF.

Support SEC-permitted image formats, primarily JPG and GIF, according to the manual.

Handle:

- Logos
- Charts
- Diagrams
- Signatures
- Embedded images
- Supported vector graphics requiring raster conversion

Preserve image dimensions and proportions.

Avoid unnecessary quality loss.

Do not convert ordinary text into images.

Use deterministic, compliant filenames such as:

```text
image001.jpg
image002.gif
image003.jpg
```

Validate that:

- Every referenced image exists.
- All images use permitted formats.
- No external images are referenced.
- No unused images are included.
- All asset references are relative and valid.
- No image is corrupted.

All final image assets must be placed in the ZIP root.

---

# 9. VISUAL VALIDATION ENGINE

Implement automated page-by-page visual regression.

## Rendering

Render the generated PDF at a controlled DPI.

Render the generated HTM using Playwright and Chromium.

Use reproducible:

- Browser versions
- Viewport dimensions
- Scale factors
- Font environments
- Rendering settings

## Comparison

Detect:

- Text displacement
- Missing content
- Font substitution
- Font-size mismatch
- Incorrect line wrapping
- Table misalignment
- Border discrepancies
- Missing graphics
- Image displacement
- Incorrect margins
- Vertical spacing differences
- Page-boundary differences
- Text overflow

Calculate pixel-difference metrics.

Also perform content-integrity and geometry-based comparisons.

Pixel-difference metrics alone are insufficient to establish correctness.

## Strict Fidelity Mode

Implement strict validation that requires zero unexplained visual discrepancies under the configured comparison method.

Distinguish actual layout differences from antialiasing and renderer-specific pixel differences.

Never conceal structural discrepancies through aggressive image normalization.

Attempt safe layout corrections only when they remain EDGAR-compliant.

If exact visual matching is impossible, report the unresolved differences and fail strict validation.

Do not label output pixel-perfect without evidence.

---

# 10. FINAL OUTPUT REQUIREMENTS

The output ZIP filename must match the uploaded DOCX basename.

Example:

Input:

```text
06749LWD4_prelim_prospectus_automated.docx
```

Output:

```text
06749LWD4_prelim_prospectus_automated.zip
```

Inside the ZIP:

```text
06749LWD4_prelim_prospectus_automated.zip
│
├── 06749LWD4_prelim_prospectus.htm
├── image001.jpg
├── image002.gif
└── image003.jpg
```

The internal HTM filename must comply with the EDGAR manual's filename limits.

Shorten it deterministically when required.

The final ZIP must contain only:

1. Exactly one `.htm` document.
2. Its referenced JPG/GIF assets.

All files must be at the root.

Do not include:

- DOCX
- PDF
- JSON
- CSS
- JavaScript
- Logs
- Screenshots
- Validation reports
- README
- Nested directories
- Unused assets

Before making the ZIP downloadable, validate its complete contents.

Keep intermediate documents and diagnostic reports available only through the application's authorized internal processing workflow.

---

# 11. WEB APPLICATION INTERFACE

Create a professional, responsive, accessible interface.

Use Next.js, React JSX, Tailwind CSS, DaisyUI, and Lucide icons.

Support light and dark modes.

## Main Features

### Upload

- Drag-and-drop DOCX upload
- File picker
- Multiple files
- File-size limits
- File validation
- Upload progress

### Conversion Dashboard

Display each document and its processing stages:

1. Uploaded
2. Validating
3. Accepting revisions
4. Generating PDF
5. Analyzing PDF
6. Generating HTM
7. Preparing assets
8. Validating SEC compliance
9. Comparing formatting
10. Packaging ZIP
11. Completed or Failed

### Preview

Implement an internal preview system supporting:

- PDF preview
- HTM preview
- Side-by-side comparison
- Zoom controls
- Page navigation
- Synchronized scrolling
- Difference overlays
- Highlighting formatting discrepancies

### Download

Allow ZIP download after successful validation.

For failed conversions, show detailed diagnostics.

Do not present unsuccessful files as SEC-ready.

### Batch Processing

Support several DOCX uploads.

Generate one ZIP per input file.

Maintain independent job progress, failures, and download controls.

---

# 12. BACKEND API

Implement versioned REST endpoints.

Suggested API:

```text
POST   /api/v1/conversions
GET    /api/v1/conversions/{job_id}
GET    /api/v1/conversions/{job_id}/events
GET    /api/v1/conversions/{job_id}/preview
GET    /api/v1/conversions/{job_id}/validation
GET    /api/v1/conversions/{job_id}/download
DELETE /api/v1/conversions/{job_id}
GET    /api/v1/health
GET    /api/v1/readiness
```

Implement:

- Secure uploads
- File validation
- Job creation
- Asynchronous processing
- Progress tracking
- Structured errors
- Retries
- Cancellation
- Download authorization
- File cleanup
- Worker health monitoring
- Job expiration

Use clean service boundaries and structured logging.

---

# 13. SECURITY AND PERFORMANCE

Treat all uploaded documents as untrusted and potentially confidential.

Implement:

- Authentication or configurable access control
- File-type verification
- ZIP-bomb protection
- File-size limits
- Timeouts
- Memory limits
- CPU limits
- Isolated workspaces
- Path traversal protection
- No macro execution
- No arbitrary code execution
- Restricted outbound network access
- Secure downloads
- Unpredictable job identifiers
- Temporary-file cleanup
- Configurable retention periods
- Sensitive-data-safe logging

Optimize for:

- Efficient worker utilization
- Low memory consumption
- Controlled concurrency
- Streaming uploads
- Lazy page analysis
- Reusable rendering workers
- Deterministic output
- Minimal unnecessary temporary files
- Stable processing of large documents

Security and correctness must take priority over performance shortcuts.

---

# 14. PROJECT STRUCTURE

Use the following structure as a starting point.

```text
edgar-converter/
│
├── apps/
│   └── web/
│       ├── app/
│       ├── components/
│       ├── hooks/
│       ├── lib/
│       ├── public/
│       └── package.json
│
├── services/
│   └── api/
│       ├── app/
│       │   ├── api/
│       │   ├── core/
│       │   ├── models/
│       │   ├── schemas/
│       │   ├── services/
│       │   └── main.py
│       └── pyproject.toml
│
├── packages/
│   └── converter/
│       ├── revisions/
│       ├── pdf_export/
│       ├── pdf_analysis/
│       ├── layout/
│       ├── html_generator/
│       ├── assets/
│       ├── sec_validation/
│       ├── visual_validation/
│       ├── packaging/
│       └── pipeline.py
│
├── workers/
│   ├── tasks/
│   └── worker.py
│
├── tests/
│   ├── fixtures/
│   ├── unit/
│   ├── integration/
│   ├── regression/
│   └── e2e/
│
├── docs/
│   ├── architecture.md
│   ├── conversion-pipeline.md
│   ├── sec-compliance.md
│   ├── deployment.md
│   └── limitations.md
│
├── infrastructure/
│   ├── docker/
│   └── deployment/
│
├── AGENTS.md
├── PROJECT_STATUS.md
├── .agent-checkpoint.json
├── .env.example
├── .gitignore
└── README.md
```

Do not initialize Git.

Do not overwrite unrelated existing project files.

You may improve the directory structure if justified and documented.

---

# 15. PERSISTENT AI AGENT PROGRESS TRACKING

**This section is mandatory and must be implemented during Stage 1.**

The project must remain understandable and resumable even if:

- The current conversation becomes too long.
- Chat context is truncated.
- The chat session is lost.
- The user starts a completely new conversation.
- A different AI agent takes over development.
- Development resumes after several days or weeks.

Do not rely on chat history as the only source of project progress.

Persist project knowledge directly in repository files.

## 15.1 AGENTS.md

Create and maintain `AGENTS.md` in the project root.

This is the primary onboarding document for any AI coding agent.

It must include:

- Project purpose
- Technology stack
- High-level architecture
- Coding conventions
- Directory structure
- SEC compliance constraints
- PDF-first conversion requirement
- Pixel-fidelity requirement
- ZIP output restrictions
- Testing requirements
- Git restrictions
- Stage-by-stage workflow
- Progress recovery instructions
- Links to important project documentation

Add the following mandatory instruction near the beginning:

**Before implementing any changes, every AI agent must read `AGENTS.md`, `PROJECT_STATUS.md`, and `.agent-checkpoint.json` and inspect the current repository state.**

Do not assume the previous AI agent completed the stage correctly.

Verify relevant files and tests before continuing.

## 15.2 PROJECT_STATUS.md

Create a detailed, human-readable project status file.

This must be updated after every meaningful development milestone.

Suggested structure:

```text
# EDGAR Converter — Project Status

## Overall Status
Current Stage:
Stage Status:
Last Completed Stage:
Next Stage:
Last Updated:

## Project Objective
...

## Completed Stages
...

## Current Stage
...

## Implemented Features
...

## Files Created or Modified
...

## Tests Executed
...

## Known Bugs
...

## Technical Limitations
...

## Architectural Decisions
...

## Pending Tasks
...

## Next Actions
...

## Suggested Commit Message
...

## Resume Instructions
...
```

Do not mark a stage completed unless the required implementation and relevant tests have actually been performed.

If a stage is blocked, record it as blocked.

If a test has not been executed, explicitly state that.

## 15.3 .agent-checkpoint.json

Create a machine-readable checkpoint file in the project root.

Example:

```json
{
  "project": "edgar-converter",
  "schema_version": 1,
  "current_stage": 1,
  "current_stage_name": "Requirements and Architecture",
  "stage_status": "not_started",
  "last_completed_stage": 0,
  "next_stage": 1,
  "authorization_required": true,
  "awaiting_user_approval": false,
  "last_updated": null,
  "completed_stages": [],
  "implemented_components": [],
  "pending_tasks": [],
  "known_issues": [],
  "last_test_results": [],
  "suggested_commit_message": null,
  "git_operations_performed": false,
  "notes": []
}
```

Keep this file synchronized with `PROJECT_STATUS.md`.

Allowed stage statuses:

- `not_started`
- `in_progress`
- `completed`
- `blocked`
- `awaiting_user_approval`

Update the checkpoint atomically where possible.

Never invent successful test results.

Do not use the checkpoint to bypass the manual approval requirement.

## 15.4 Development Decision Log

Create:

`docs/decisions.md`

Record important architectural decisions.

Each entry should contain:

- Date
- Decision
- Context
- Alternatives considered
- Reasoning
- Consequences

Examples:

- PDF rendering engine selection
- Revision-acceptance strategy
- EDGAR HTML reconstruction approach
- Visual comparison methodology
- Worker isolation design
- File storage strategy

This helps a new AI agent understand why particular implementations were chosen.

## 15.5 Test History

Create:

`docs/test-history.md`

After each development stage, record:

- Stage
- Test command
- Test environment
- Result
- Number of passing tests
- Number of failing tests
- Outstanding failures

Do not replace previous test history.

Append new records so progress remains auditable.

## 15.6 Context Recovery Protocol

Whenever a new conversation or AI agent begins work:

1. Read `AGENTS.md`.
2. Read `PROJECT_STATUS.md`.
3. Read `.agent-checkpoint.json`.
4. Read `docs/decisions.md`.
5. Read relevant entries in `docs/test-history.md`.
6. Inspect the existing project files.
7. Inspect read-only Git status and diffs if Git is available.
8. Determine the last verified completed stage.
9. Identify the current pending tasks.
10. Verify critical assumptions and relevant test results.
11. Determine whether the previous stage is awaiting user approval.
12. Continue only if the user has explicitly authorized the next stage.

Do not restart the entire project.

Do not repeat completed work unnecessarily.

Do not assume an implementation is correct merely because a checkpoint says it is complete.

If progress records conflict with the actual code, prioritize verified repository state and report the discrepancy.

## 15.7 Recovery From Interrupted Work

If a stage was interrupted:

- Identify completed tasks.
- Identify incomplete tasks.
- Inspect partially modified files.
- Re-run relevant tests.
- Resume the unfinished stage.
- Update progress records.

If the checkpoint says `awaiting_user_approval`, do not start the next stage without explicit authorization.

If the prior stage is complete but its Git changes remain uncommitted, leave them untouched and wait for the user's instruction.

Never automatically commit or push changes during recovery.

---

# 16. STRICT GIT RESTRICTIONS

**These restrictions override all other instructions.**

You are prohibited from performing Git operations that modify repository state.

Never execute:

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

Do not create, delete, or modify branches or tags.

Do not initialize Git, even if the project directory is empty.

Do not create commits.

Do not push changes.

Do not stage files.

Do not perform Git write operations through an IDE, API, library, shell script, automation, or another tool.

Read-only commands are allowed, including:

```text
git status
git diff
git log
```

Creating and modifying normal project files is permitted.

All Git state changes are the user's responsibility.

Provide suggested commit messages as plain text only.

---

# 17. STAGE-BY-STAGE DEVELOPMENT

Implement the system in the exact following order.

## Stage 1 — Requirements Analysis and Architecture

- Inspect reference files.
- Extract SEC requirements.
- Inspect existing project structure.
- Design architecture.
- Define module interfaces.
- Create documentation.
- Create `AGENTS.md`.
- Create `PROJECT_STATUS.md`.
- Create `.agent-checkpoint.json`.
- Create decision and test history documents.

Do not implement later stages.

## Stage 2 — Backend Foundation

- Initialize application files, not Git.
- Create FastAPI service.
- Implement configuration.
- Create upload endpoints.
- Implement job management.
- Configure Redis and Celery.
- Establish worker infrastructure.
- Implement secure temporary storage.
- Add basic API tests.

## Stage 3 — DOCX Processing

- Implement revision detection.
- Implement revision acceptance.
- Implement clean DOCX generation.
- Implement PDF export.
- Validate PDF output.
- Compare against the supplied reference.
- Add automated tests.

## Stage 4 — PDF Layout Analysis

- Implement PDF parsing.
- Extract text and typography.
- Extract image geometry.
- Detect tables.
- Analyze vector objects.
- Build the intermediate layout model.
- Add extraction tests.

## Stage 5 — PDF-to-HTM Reconstruction

- Implement permitted HTML generation.
- Reconstruct text formatting.
- Reconstruct tables.
- Preserve spacing.
- Handle complex layouts.
- Generate valid `.htm`.
- Add conversion tests.

## Stage 6 — SEC Compliance Engine

- Implement versioned manual-derived rules.
- Validate HTML.
- Validate attributes.
- Validate hyperlinks.
- Validate characters.
- Validate assets.
- Validate filenames.
- Implement detailed diagnostics.

## Stage 7 — Pixel-Level Visual Validation

- Render PDF pages.
- Render HTM pages.
- Compare text positions.
- Compare page appearance.
- Detect formatting discrepancies.
- Generate internal visual-difference artifacts.
- Add strict validation behavior.

## Stage 8 — ZIP Packaging

- Implement deterministic ZIP naming.
- Implement compliant HTM naming.
- Package root-level assets.
- Validate ZIP contents.
- Reject invalid packages.
- Add packaging tests.

## Stage 9 — Next.js Frontend

- Build responsive application interface.
- Implement DOCX upload.
- Implement batch selection.
- Implement processing dashboard.
- Implement job progress.
- Implement preview.
- Implement comparison controls.
- Implement ZIP download.
- Add accessibility and UI tests.

## Stage 10 — Full Integration and Testing

- Integrate frontend and backend.
- Run the complete conversion pipeline.
- Test the Barclays reference.
- Compare all 23 pages.
- Diagnose formatting differences.
- Fix application defects.
- Execute integration and E2E tests.

## Stage 11 — Deployment Configuration

- Prepare Docker configuration for compatible services.
- Document rendering-worker infrastructure.
- Configure environment variables.
- Add security hardening.
- Add cleanup policies.
- Add health checks.
- Prepare deployment documentation.

## Stage 12 — Final Audit and Optimization

- Review the entire codebase.
- Remove dead code.
- Review dependencies.
- Optimize performance.
- Check memory usage.
- Verify worker stability.
- Run security checks.
- Run the full automated test suite.
- Verify ZIP restrictions.
- Review SEC compliance.
- Review visual fidelity.
- Finalize documentation.

---

# 18. MANDATORY STAGE COMPLETION GATE

**Implement exactly one stage per user authorization.**

For each stage:

1. Read the persistent project context.
2. Verify the current stage.
3. Implement only that stage.
4. Run relevant tests.
5. Fix defects within the stage.
6. Update `PROJECT_STATUS.md`.
7. Update `.agent-checkpoint.json`.
8. Update `docs/test-history.md`.
9. Update architectural decisions where applicable.
10. Report the stage results.
11. Provide a suggested Git commit message.
12. Stop execution.

Do not start the next stage automatically.

The user will manually review the changes, commit them, and push them.

Only continue after the user explicitly says to continue or begin the next stage.

A user message reporting that a commit has been completed is not automatically authorization to continue unless that intent is explicitly stated.

Do not interpret silence as approval.

## Required Stage Report

Use this format:

### Stage [N] — [Stage Name]

**Status:** Completed / Blocked

**Implemented**

- Actual changes made
- Important files created or modified
- Technical decisions

**Tests**

- Commands executed
- Passed tests
- Failed tests
- Remaining limitations

**Progress Tracking**

- `AGENTS.md` updated if necessary
- `PROJECT_STATUS.md` updated
- `.agent-checkpoint.json` updated
- Test history updated

**Suggested Commit Message**

```text
feat: implement [stage description]
```

**Next Stage:** Stage [N+1] — [Name]

**Action Required:** Review the changes, commit and push manually, then explicitly instruct me to continue.

Stop after this report.

Do not run Git write commands.

---

# 19. HANDLING BLOCKERS AND FAILURES

If implementation is blocked:

1. Identify the blocker.
2. Explain the cause.
3. Preserve completed work.
4. Record the blocker in progress files.
5. Record unsuccessful tests.
6. Suggest the next corrective action.
7. Provide a commit message only if meaningful changes were completed.
8. Stop and wait for instructions.

Do not fabricate results.

Do not mark incomplete functionality as completed.

Do not silently skip mandatory requirements.

If a particular document cannot meet SEC compliance and strict visual fidelity simultaneously, retain a clear diagnostic record.

---

# 20. TESTING REQUIREMENTS

Implement automated tests covering:

### Unit Tests

- Revision detection and acceptance
- PDF layout extraction
- Text positioning
- Table reconstruction
- Character encoding
- HTML tag validation
- HTML attribute validation
- Image processing
- Filename normalization
- ZIP inspection

### Integration Tests

- DOCX to accepted DOCX
- Accepted DOCX to PDF
- PDF to layout model
- Layout model to HTM
- Asset generation
- SEC compliance validation
- Visual comparison
- Final ZIP generation

### End-to-End Tests

- Upload DOCX
- Create job
- Process document
- Display progress
- Validate output
- Preview results
- Download ZIP
- Inspect ZIP contents

### Regression Tests

Use the uploaded Barclays reference.

Verify:

- Accepted DOCX content
- PDF page count and dimensions
- PDF layout
- Text integrity
- Tables
- Footnotes
- Vertical text
- Graphics
- Special characters
- HTM compliance
- HTM visual differences
- ZIP structure

Test all 23 pages.

Do not test only the first page.

Add additional fixtures for other document types where useful.

Document which cases pass and which remain unsupported.

---

# 21. ENGINEERING QUALITY STANDARDS

Follow these practices:

- Clean architecture
- Modular code
- Reusable components
- Clear service boundaries
- Meaningful naming
- Comprehensive error handling
- Structured logging
- Deterministic processing
- Minimal dependencies
- Automated tests
- Security-first file handling
- Performance-conscious implementation

Frontend code must use React JSX rather than TypeScript.

Avoid unnecessary basic explanations in technical documentation.

Focus on implementation details, maintainability, and scalability.

For UI development:

- Follow modern Figma-quality design conventions.
- Maintain consistent spacing and typography.
- Use accessible interaction patterns.
- Support keyboard navigation.
- Use responsive layouts.
- Avoid decorative elements that reduce usability.

Never sacrifice document correctness for a visually polished interface.

---

# 22. DOCUMENTATION REQUIREMENTS

Maintain:

### README.md

Include:

- Project overview
- Features
- Requirements
- Installation
- Local development
- Environment configuration
- Application usage
- Architecture
- Testing
- Deployment
- Troubleshooting

### AGENTS.md

Include:

- AI agent onboarding
- Architecture
- Engineering rules
- SEC requirements
- PDF-first workflow
- Git restrictions
- Stage execution protocol
- Context recovery

### PROJECT_STATUS.md

Include:

- Completed stages
- Current stage
- Progress
- Implemented functionality
- Tests
- Known issues
- Next actions
- Suggested commit message

### .agent-checkpoint.json

Maintain synchronized machine-readable progress.

### docs/decisions.md

Track architectural decisions.

### docs/test-history.md

Maintain an auditable testing history.

### docs/sec-compliance.md

Document EDGAR rules and manual references.

### docs/limitations.md

Document unsupported document features and fidelity limitations.

### docs/deployment.md

Document local and production deployment.

---

# 23. DEFINITION OF DONE

The complete system is functionally ready when:

- The web application runs.
- DOCX upload works.
- Tracked changes are accepted correctly.
- PDF generation works.
- PDF layout analysis works.
- HTM generation works.
- SEC compliance validation works.
- Text integrity is verified.
- Image extraction works.
- Visual comparison works.
- ZIP packaging works.
- Batch processing works.
- Secure downloads work.
- Relevant automated tests pass.
- Project documentation is complete.
- Deployment configuration is available.
- Persistent progress tracking is implemented.
- A new AI agent can recover project context from repository files.

The system must not claim that every arbitrary DOCX can achieve pixel-perfect SEC-compliant HTML rendering unless that claim is supported by actual tests.

Any document that fails strict fidelity validation must be reported as unsuccessful rather than silently accepted.

---

# 24. FINAL EXECUTION INSTRUCTIONS

Start by reading the repository's existing project files.

If `AGENTS.md`, `PROJECT_STATUS.md`, or `.agent-checkpoint.json` already exist, read them before doing any work.

If progress records exist, recover the current development stage.

Do not reset or restart completed development.

If no progress records exist, begin Stage 1.

For Stage 1:

1. Inspect the four reference documents.
2. Inspect the existing project directory.
3. Extract applicable SEC rules.
4. Define the system architecture.
5. Establish the conversion and validation strategy.
6. Create persistent progress-tracking files.
7. Document important technical decisions.
8. Perform relevant verification.
9. Update project progress.
10. Report Stage 1 completion and provide its suggested commit message.

Then stop.

Do not begin Stage 2 until explicitly instructed.

## FINAL NON-NEGOTIABLE RULES

**Never initialize Git.**

**Never stage files.**

**Never create commits.**

**Never push changes.**

**Never modify Git branches or repository history.**

**Never proceed to the next stage without explicit user authorization.**

**Never rely exclusively on chat history for project progress.**

**Always maintain persistent, accurate, recoverable project state.**

**Always report completed work, testing results, and the suggested commit message at the end of each stage.**

**Always stop after completing the authorized stage.**

Begin Stage 1 now.
