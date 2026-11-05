# Stage 8 ZIP packaging and download eligibility

`converter.packaging` (converter 0.8.0) implements bounded ZIP creation and independent byte validation. This stage does not qualify the Word fixture, unresolved SEC permissions or current screen differences. No full-chain successful filing/download has been demonstrated. Archive-mechanics success is explicitly `conversion_eligible=false`.

## Names and immutable filing bytes

The downloaded ZIP retains the admitted DOCX basename, including Unicode and case, with `.zip` replacing `.docx`. Its server path is the current private attempt's `package/result.zip`; client names are never used as server paths. The response uses RFC 5987 UTF-8 Content-Disposition encoding.

The internal HTM is lowercase ASCII within the manual-derived 32-character limit. A compliant short stem is retained. Otherwise the name is the first 15 sanitized stem characters, `-`, the first 12 hexadecimal SHA-256 characters of the exact original UTF-8 filename, then `.htm`. Empty/Windows-reserved stems get a document prefix. Unsafe original basenames fail. This is deterministic and separate from the outer ZIP name.

`prepare_filing_name` runs on the new normalized filing directory **before SEC and visual validation**. It updates supported literal generated self-links, checks disclosure text and fails unsupported references/collisions. Qualified HTM and references are never renamed or rewritten afterward. Earlier private candidate/normalization metadata retains its historical filename/hash; `prepared_htm_filename` and actual SEC/visual/package evidence identify final bytes.

## Publication and independent audit

`create_package` rechecks strict PDF evidence, freshly validates actual HTM/assets against stored SEC evidence, verifies production visual measurements and source/file/gate hashes, and checks current dependency/font fingerprints. Summary flags alone cannot approve a package. Inspection, failed, truncated or stale evidence fails before output creation.

The filing root must contain exactly its HTM and declared regular same-root JPG/GIF files. No symlinks, unused files or subdirectories are accepted. Captured bytes must match the freshly validated manifest. The writer creates `result.part` exclusively, fixes member timestamps to 1980-01-01, uses fixed permissions and stores members without compression. HTM comes first, followed by lexicographically sorted assets. ZIP_STORED removes zlib-version variability; larger archive size is the tradeoff. Exclusive publication as `result.zip` follows audit and final input/cancellation checks.

`audit_archive_bytes` independently reopens captured bytes and checks:

- Root-only names, exactly one HTM, duplicates/case collisions and deterministic order.
- Every member's CRC, local/central headers, contiguous offsets and bounded lengths.
- No extras, comments, encryption, links, directories, ZIP64, split archive or leading/trailing payload.
- Exact manifest hashes/sizes, permitted decoded graphics, references and actual archived SEC validation.

Names are checked before writing member bytes to a private temporary directory; `extractall` is never used. Temporary contents are removed afterward. No DOCX, PDF, report, screenshot or script enters the final ZIP. Mechanics helpers cannot mark conversions completed.

## Job lifecycle and downloads

The worker receives the original uploaded name separately from private `source.docx`. It reports `packaged` only after packaging; the repository moves the current live leased attempt to `completed` only when revision/source/content/PDF/SEC/visual/package proof is consistent. Invalid completion evidence fails with `PACKAGE_COMPLETION_INVALID`. Earlier awaiting_packaging jobs support explicit owned resume.

Polling exposes `download_available` as an eligibility hint. GET download additionally verifies ownership, retention, original source, current attempt, complete report, actual PDF/HTM/images and current rendering environment. It captures bounded ZIP bytes, checks recorded hash/length and independently audits the captured archive. Serving uses captured bytes rather than a mutable FileResponse path. State is checked before headers and periodically during streaming; expiry is checked on every chunk. Cancellation revokes access and can terminate a stream. Preview remains Stage 9 work.

Invalid/changed artifacts return 409; other owners receive 404; expired jobs receive 410. Responses retain private/no-store headers. Errors exclude disclosure text. Reports/intermediates remain in the authorized private workflow.

## Resource settings and verification

Worker settings in `.env.example`: `CONVX_PACKAGE_MAX_ARCHIVE_BYTES` (128 MiB), `CONVX_PACKAGE_MAX_UNCOMPRESSED_BYTES` (100 MiB), `CONVX_PACKAGE_MAX_MEMBER_BYTES` (64 MiB), `CONVX_PACKAGE_MAX_MEMBERS` (1001). These are product budgets, not SEC limits. The report records actual policies for revalidation. Capturing source/ZIP bytes uses bounded memory; OS storage/memory/network enforcement remains Stage 11 work.

Run `.venv/Scripts/python -m pytest tests/unit/test_packaging.py tests/integration/test_packaging_gates.py -q`. Tests write/read actual archives and use genuine PDF/SEC/Chromium failure evidence. Adversarial flag changes are rejection tests, never successful conversions. The all-page Word regression must still fail at its actual PDF gate with no package. Optional live Redis/PostgreSQL and Linux qualification remain outstanding. See [test history](test-history.md), [limitations](limitations.md) and [visual validation](visual-validation.md).
