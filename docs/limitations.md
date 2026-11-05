# Limitations and open qualification work

- Stage 1 supplies architecture, source-grounded rule design and read-only fixture inspection. There is no conversion application, running API, frontend, deployment or downloadable filing package yet.
- No revision acceptance, DOCX-to-PDF conversion, HTML reconstruction, SEC validator or visual comparison has been executed. Fixture inspection is not proof that a renderer can reproduce Word.
- Initial DOCX role labels contradicted the detected revision inventories. The user subsequently updated fixtures and current roles agree. The final inventory and reference findings record the evidence; never infer an accepted baseline solely from `(1)` in a name.
- The PDF's source mapping to an accepted DOCX must be established during Stage 3. Page count and geometry alone do not prove identical disclosure or layout.
- Commercial SDK licensing, font licenses/availability, revision/story coverage, platform support and all-page fidelity are unqualified. LibreOffice is a separately tested fallback, not an equivalent Word layout engine.
- No arbitrary document can be promised pixel-perfect EDGAR HTML. Rotated text, complex overlapping drawings, font metrics and legal markup restrictions can make strict reconstruction impossible. Such jobs must fail with diagnostics.
- The supplied manual does not provide a complete CSS property/value list in the inspected sections. MANY attributes, legacy character-reference ambiguities and conflicting attribute examples need explicit resolution before a strict profile is enabled.
- A standalone HTML/image ZIP is not a full EDGAR submission. Form-specific requirements, MIME-expanded aggregate limits, required exhibits, Inline XBRL and filing-fee data are outside this plain-HTM converter's certification scope.
- No authorized SEC TEST submission or acceptance evidence exists. Local checks must never be described as SEC acceptance.
- Git was unavailable on PATH during initial inspection. No Git write operations were performed and no repository was initialized.
