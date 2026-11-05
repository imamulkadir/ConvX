"""Fixture/recovery checks across original and refactor workflows; no conversion certification."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


class StageOneChecks(unittest.TestCase):
    def setUp(self):
        self.inventory = read_json("docs/fixture-inventory.json")
        self.files = {Path(f["path"]).name: f for f in self.inventory["files"]}

    def test_fixture_hashes_and_sizes(self):
        self.assertEqual(len(self.files), 5)
        for record in self.files.values():
            path = ROOT / record["path"]
            self.assertEqual(path.stat().st_size, record["bytes"])
            with path.open("rb") as stream:
                self.assertEqual(hashlib.file_digest(stream, "sha256").hexdigest(), record["sha256"])

    def test_docx_role_evidence(self):
        original = self.files["06749LWD4_prelim_prospectus_automated.docx"]
        accepted = self.files["06749LWD4_prelim_prospectus_automated (1).docx"]
        self.assertEqual(original["revisions"], {"word/document.xml": {"del": 14, "ins": 17}})
        self.assertEqual(accepted["revisions"], {})
        for record in (original, accepted):
            self.assertIsNone(record["zip_crc_failure"])
            self.assertEqual(record["other_change_elements"], {})
            self.assertEqual(record["tables"], 14)

    def test_all_reference_pdf_pages(self):
        pdf = self.files["06749LWD4_prelim_prospectus_automated.pdf"]
        self.assertEqual(pdf["page_count"], 23)
        self.assertFalse(pdf["encrypted"])
        self.assertEqual([p["page"] for p in pdf["pages"]], list(range(1, 24)))
        for page in pdf["pages"]:
            self.assertEqual(page["media_box_pt"], [0, 0, 612, 792])
            self.assertEqual(page["rotation"], 0)
            self.assertGreater(page["extracted_characters"], 0)

    def test_manual_identity(self):
        manual = self.files["edgarfm-vol2-v78.pdf"]
        self.assertEqual(manual["page_count"], 607)
        for text in ("Volume II", "VERSION 78", "September 14, 2026"):
            self.assertIn(text, manual["title_page_text"])
        registry = read_json("docs/compliance/efm-v78.rules.json")
        self.assertEqual(registry["manual"]["sha256"], manual["sha256"])

    def test_rule_evidence_and_uncertainties(self):
        registry = read_json("docs/compliance/efm-v78.rules.json")
        self.assertFalse(registry["executable_validator"])
        self.assertFalse(registry["strict_profile_approved"])
        rules = registry["rules"]
        self.assertEqual(len({r["id"] for r in rules}), len(rules))
        self.assertTrue(any(r["status"] == "unresolved" for r in rules))
        for rule in rules:
            self.assertTrue(rule["section"])
            self.assertTrue(rule["requirement"])
            self.assertIn(rule["status"], {"confirmed_manual", "project_policy", "unresolved"})

    def test_required_docs_and_local_links(self):
        required = ["README.md", "AGENTS.md", "PROJECT_STATUS.md", "docs/architecture.md",
                    "docs/interfaces.md", "docs/conversion-pipeline.md", "docs/sec-compliance.md",
                    "docs/deployment.md", "docs/limitations.md", "docs/decisions.md",
                    "docs/test-history.md", "docs/reference-findings.md"]
        for name in required:
            path = ROOT / name
            text = path.read_text(encoding="utf-8")
            self.assertGreater(len(text), 100, name)
            for link in re.findall(r"\]\(([^)]+)\)", text):
                if "://" in link or link.startswith("#"):
                    continue
                self.assertTrue((path.parent / link.split("#")[0]).exists(), f"{name}: {link}")

    def test_progress_records_agree(self):
        checkpoint = read_json(".agent-checkpoint.json")
        status = (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(checkpoint["current_stage"], 1)
        self.assertEqual(checkpoint["next_stage"], checkpoint["current_stage"] + 1)
        self.assertIn(f"Stage Status: {checkpoint['stage_status']}", status)
        self.assertIn(f"Last Completed Stage: {checkpoint['last_completed_stage']}", status)
        self.assertFalse(checkpoint["git_operations_performed"])
        self.assertTrue(checkpoint["authorization_required"])
        self.assertIn("Before implementing any changes, every AI agent must read", (ROOT / "AGENTS.md").read_text(encoding="utf-8"))

    def test_stage_scope(self):
        checkpoint = read_json(".agent-checkpoint.json")
        if checkpoint.get("workflow") == "simplification-refactor":
            self.assertEqual(checkpoint["schema_version"], 2)
            self.assertTrue((ROOT / "docs/refactor-audit.md").is_file())
            legacy = read_json("docs/history/pre-refactor-checkpoint.json")
            self.assertGreaterEqual(legacy["last_completed_stage"], 1)
            self.assertTrue((ROOT / "packages/converter/pipeline.py").is_file())
            return  # Existing-project audit; the historical empty-project assertion is inapplicable.
        if checkpoint["current_stage"] > 1:
            self.assertIn(1, checkpoint["completed_stages"])
            return  # Stage 1's historical absence-of-application assertion no longer applies.
        # No later-stage application implementation is delivered by this stage.
        for directory in ("apps", "services", "packages/converter", "workers"):
            path = ROOT / directory
            files = list(path.rglob("*")) if path.exists() else []
            self.assertFalse(any(p.suffix in {".py", ".js", ".jsx", ".ts", ".tsx"} for p in files))


if __name__ == "__main__":
    unittest.main(verbosity=2)
