# Reference fixture findings — 2026-11-05

The workspace initially contained `AGENTS.md` and four fixtures, without code or progress records. Searched `D:/Tools`, and the current user's Downloads, Documents and Desktop. Located Volume II v78 in Downloads and copied it to fixtures without changing its bytes. Volume I v43 remains supplemental. No reference bytes were edited by the agent.

The user replaced the two DOCX fixture contents during Stage 1. Re-inspection after that update is authoritative; current [inventory](fixture-inventory.json) records hashes, ZIP CRC results, revision counts, media paths and every PDF page. The initial hashes appeared under the opposite DOCX names; the current roles now agree with the requirements.

| Role | Current fixture | Verified observations |
| --- | --- | --- |
| Original | `06749LWD4_prelim_prospectus_automated.docx` | SHA-256 `9a9c22ddb0c496bde3dda78f70f0e267e30efd4b8cb410807d2846fbcdda666a`; 17 insertions, 14 deletions in document.xml; 14 tables, 5 section-property elements, 5 media parts; valid ZIP CRC |
| Expected accepted | `06749LWD4_prelim_prospectus_automated (1).docx` | SHA-256 `ad2c5274f9949e19f655386143e8087e925411e6b4daf9ece2e1b1a5f70cb33d`; no inventoried revision markers; 14 tables, 5 section-property elements, 9 media parts; valid ZIP CRC |
| Reference PDF | `06749LWD4_prelim_prospectus_automated.pdf` | SHA-256 `4e978ec13451024838908889839548d6bee4c559c7c33e5ed3aa19f0a85b2431`; all 23 pages 612 x 792 pt, rotation 0, unencrypted; text extracted on every page; metadata identifies Word for Microsoft 365 |
| Primary manual | `edgarfm-vol2-v78.pdf` | SHA-256 `816bbe2b5d2677ddc94e6199b446a8a856a54596704021a7b9ff592c0bc26cf3`; 607 pages; title confirms Volume II v78 September 14, 2026 |
| Supplemental manual | `edgarfm-vol1-v43.pdf` | SHA-256 `1abb4c0faf4ce9261fddc147fb2cf28ffe4ba434b0cc7420707c0d001511aeb7`; 13 pages; Volume I v43 March 16, 2026 |

Filename aliases: accepted DOCX has a space before `(1)`; the reference PDF lacks `(1)`. No renamed duplicates were manufactured. Stage 3 must inspect why the accepted document has more media parts and determine active/orphaned relationships rather than assume package equality.

Inventory scans all Word XML parts for defined revision markers and other `*Change` elements. This does not prove comprehensive extension/story coverage, semantic acceptance equivalence, image preservation or renderer fidelity. Page count and extracted-character counts do not prove content correctness or visual similarity. Stage 3 must establish accepted content and PDF correspondence. No PDF was generated in Stage 1.
