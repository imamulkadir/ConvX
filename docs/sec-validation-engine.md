# SEC compliance engine - Stage 6

The free local validator checks actual HTM bytes and explicitly declared graphic files. It is not an SEC acceptance service and sends no document or credential to EDGAR. Entry point: `converter.sec_validation.validator.validate_files(htm, assets, submission, policy, context)`. A standalone CLI is available:

```powershell
.venv/Scripts/python -m converter.sec_validation.cli var/stage6/plain/filing.htm
.venv/Scripts/python -m converter.sec_validation.cli var/stage6/plain/filing.htm --form-type S-1 --encoded-submission-bytes 10000
```

The second argument is the actual MIME-encoded size of the entire submission, supplied by its authorized assembler. Do not substitute ZIP size or an estimate. CLI output is structured diagnostics/hashes, without disclosure excerpts. Exit zero requires the strict local result; missing context or failed/unresolved checks exit 2. These example paths are private regression artifacts, not user uploads or successful prospectus conversions.

## Versioned authority and uncertainty

Runtime [registry v78.2](compliance/efm-v78.2.rules.json) is shipped as package data and hashed in every result. Its manual SHA is pinned to the supplied 607-page Volume II v78, September 14, 2026. The [historical v78.1 design registry](compliance/efm-v78.rules.json) and Stage 5 proposed profile remain unchanged. Rules distinguish confirmed manual text, supplementary SEC guidance, stricter product constraints and unresolved permissions.

Sections 5.1.1 and 5.2.2.1-.10 supply filenames, tags/attributes, references, encoding and applicable size limits. The manual explicitly allows PAGE/R in 5.2.2.8 even though they are absent from its main body-tag table. PAGE is recognized; R/redlining is recognized as manual-supported but rejected by the accepted-final product profile. Listed legacy/interactive elements such as ISINDEX/XMP/PLAINTEXT are rejected as unsupported product semantics, not falsely called SEC-prohibited elements. No Inline XBRL, arbitrary submission attachment set, test filing or final ZIP is implemented here.

STYLE is explicitly listed for MANY elements. Neither the supplied Chapter 5 nor the checked supplementary SEC guidance enumerates a complete per-tag CSS property/value allowlist. The implemented safe literal grammar rejects active/URL/escape/function/hidden/unsupported declarations, but does not mistake security safety or ordinary browser support for SEC permission. Actual use of unresolved MANY/CSS permissions produces error diagnostics (`ATTRIBUTE_SCOPE_UNVERIFIED`, `CSS_PERMISSION_UNVERIFIED`) and strict failure. Unused uncertainties do not prevent a document using only confirmed rules from passing the local subset. W3C syntax alone does not override manual restrictions.

The manual's character table contains legacy C1 values and conflicting symbol descriptions. The profile accepts ASCII bytes, Latin-1 references, and a narrow set of explicit manual named mappings cross-checked against W3C HTML4. C1 numeric references are rejected to avoid browser remapping; other unverified Unicode mappings fail rather than being transliterated. `&bull;`, smart quotes, Euro/Greek and other mappings outside this confirmed subset need further evidence. This is a conservative profile limitation, not a claim that EDGAR rejects every such character. Raw extended bytes fail; their intended disclosure must be preserved with verified references.

## Actual-file checks

The source scanner observes tags/attributes before lxml or a browser repairs markup, so raw TBODY/SPAN/nested TABLE and duplicate attributes cannot be hidden by parsing. It handles omitted table end tags without inventing a general SEC proper-nesting requirement. Active/event/restricted/unlisted constructs, ambiguous declarations/comments, unsupported XML processing instructions and multiple document containers produce explicit failures. Literal CSS grammar is checked separately from unresolved permissions.

Links are never fetched. The ordinary profile permits specified SEC Archives HTTPS targets, self-file and internal bookmarks. It rejects credentials, deceptive hosts, traversal, network paths, active schemes, encoded ambiguity and missing/duplicate destinations. Other local submission links can be manual-permitted but are outside the product's one-HTM artifact manifest and fail with a product-context diagnostic. IMG references must be exact case-sensitive root-relative JPG/GIF names in the explicit manifest; remote/data/SVG/missing/unused assets fail. The validator does not recursively expose or include intermediate workspace files.

Filenames enforce the actual 32-character ASCII convention and the product's .htm/.jpg/.gif extensions. Assets are checked by real decoding, extension/encoding agreement, dimensions, corruption and pixel budgets. Animated GIF is excluded by the static product profile, not asserted to be a blanket manual prohibition. Source/file hashes are checked again before the result is returned. Nodes/depth/attributes/diagnostics, individual and aggregate bytes, file count and decoded pixels are bounded, with cancellation/deadline checks. Native decoding/parsing still needs deployment OS isolation.

Diagnostics include stable code, severity, file, source element/line where available, relevant section/source, rule basis and remediation. Counts aggregate repeated occurrences without copying disclosure. A limit/incomplete scan cannot pass.

## Asset materialization and fidelity

After generation, `normalize_assets` verifies PDF/candidate hashes and request identity, checks image xrefs/soft-mask geometry before decoding, and creates a new private `filing/` directory. It copies the candidate and only normalizes IMG src values; disclosure text is checked unchanged. No complete page or disclosure text is rasterized.

Original JPEG bytes are retained where possible. Small-palette graphics use GIF only when decoded RGB pixels roundtrip exactly. Other graphics use JPEG at quality 100 with chroma subsampling disabled; the report explicitly records whether decoded pixels changed. Supported source alpha is composited onto the generator's white canvas. Only a top-level full-page Normal/opacity-1 group can be flattened under this profile, with a pending visual check; other compositing remains rejected. Source and normalized dimensions, hashes, formats, alpha/passthrough/exactness metadata are recorded. Repeated placements reuse one image. Any lossy or compositing difference still needs Stage 7 review and can fail strict fidelity.

The generator is now `convx-flow-htm-v2` / `efm78-stage6-candidate-v1`: equivalent characters share formatting runs instead of independent word/character wrappers, following SEC supplementary filing guidance. Source character accounting remains exact; browser shaping inside runs is unmeasured. The manual-derived CSS permission gap is retained rather than bypassed by this change. Historical Stage 5 candidate hashes/results remain historical.

## Results, integration and limits

`passed` means complete local document/asset checks succeeded for the implemented subset. `strict_passed` additionally requires supplied form/whole encoded submission size accounting. Both are local results; `sec_acceptance_confirmed` and visual fidelity remain false. Ordinary 200 MB, specified 600 MB forms and combined 800 MB limits use conservative decimal MB. ABS-15G additionally checks actual HTML bytes against 25 MB. Combined 10-D/ABS-EE cannot be strictly qualified from a total alone: separate component accounting remains required and explicitly fails as unresolved.

The worker writes `asset_normalization` and `sec_validation` into its current private attempt report. Actual failures, including unresolved permissions, end as `SEC_VALIDATION_FAILED`. A passing local file gate would stop at `blocked / awaiting_visual_validation / VISUAL_ENGINE_NOT_AVAILABLE`; overall completion/download stay unavailable. Old SEC_ENGINE_NOT_AVAILABLE jobs can be explicitly resumed with a fresh attempt. The API exposes detailed local evidence only to the owner; it does not serve these private artifacts or start a UI.

The native one-page LibreOffice regression passes the PDF gate, generates/materializes HTM and correctly fails the unresolved style permissions. The Word fixture still fails all 23 PDF pages before HTM/assets/SEC processing. Confirmed-subset fixtures, real JPG/GIF decoding, malicious/ambiguous source and stale/limit/race tests establish validator behavior, not full filing acceptance. See [Stage 6 evidence](stage6-compliance-regression.json), [test history](test-history.md) and [limitations](limitations.md).

Authorized filing operators should run EDGARLink Online Doc Validation or an authorized TEST submission and reconcile the actual SEC response, as described in manual 5.2.2.10. No such submission occurred. Stage 7 requires separate explicit authorization; no Chromium visual engine or packaging/UI stage is included here.

## Research sources

- [Supplied/current official Volume II v78](https://www.sec.gov/files/edgar/filermanual/edgarfm-vol2-v78.pdf), sections cited above; all relevant local pages read without altering fixtures.
- [SEC Observe Data and Process Filing Limits](https://www.sec.gov/submit-filings/filer-support-resources/how-do-i-guides/observe-data-process-filing-limits), supplementary guidance on economical formatting, graphic references and duplicate images. Its IMG dimension advice differs in scope from the manual's explicit attribute table; this profile still reports unresolved attribute evidence.
- [W3C HTML4 character entities](https://www.w3.org/TR/html401/sgml/entities.html), mapping verification only; does not grant additional SEC permissions.
- [W3C HTML4 DTD explanation](https://www.w3.org/TR/html401/sgml/dtd.html) and [CSS2 property index](https://www.w3.org/TR/CSS2/propidx.html), syntax background only. Direct loose.dtd browsing returned unsupported content type and was not treated as evidence of EDGAR permission.
