import test from "node:test";
import assert from "node:assert/strict";
import { validateSelection, stageIndex, downloadName } from "../lib/jobs.mjs";
const limits = { max_upload_bytes: 1024, max_batch_files: 2 };
test("batch selection retains valid files and explains each rejection", () => {
  const result = validateSelection(
    [
      { name: "one.docx", size: 100 },
      { name: "bad.txt", size: 10 },
      { name: "zero.docx", size: 0 },
      { name: "large.docx", size: 1025 },
      { name: "two.DOCX", size: 200 },
      { name: "three.docx", size: 100 },
    ],
    limits,
  );
  assert.deepEqual(
    result.valid.map((file) => file.name),
    ["one.docx", "two.DOCX"],
  );
  assert.equal(result.errors.length, 4);
});
test("unknown or failed stage never implies completed progress", () => {
  assert.equal(stageIndex({ state: "failed", stage: "processing_failed" }), -1);
  assert.equal(stageIndex({ state: "running", stage: "validating_pdf" }), 4);
  assert.equal(stageIndex({ state: "completed", stage: "completed" }), 10);
});
test("download response names support Unicode and reject path separators", () => {
  assert.equal(
    downloadName(
      "attachment; filename*=utf-8''r%C3%A9sum%C3%A9.zip",
      "fallback.zip",
    ),
    "résumé.zip",
  );
  assert.equal(
    downloadName(
      "attachment; filename*=utf-8''..%2Fsecret.zip",
      "fallback.zip",
    ),
    ".._secret.zip",
  );
  assert.equal(
    downloadName("attachment; filename*=utf-8''%zz", "fallback.zip"),
    "fallback.zip",
  );
});
