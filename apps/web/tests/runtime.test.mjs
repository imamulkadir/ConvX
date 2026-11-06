import test from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  createRuntime,
  safeName,
  originCheck,
} from "../lib/server/runtime.mjs";

const project = path.resolve("../..");
test("same-origin check uses the incoming host when Next normalizes request.url", () => {
  assert.doesNotThrow(() =>
    originCheck(
      upload(undefined, "test.docx", {
        host: "127.0.0.1:3400",
        origin: "http://127.0.0.1:3400",
      }),
    ),
  );
});
function upload(
  bytes = Buffer.from("not a DOCX"),
  name = "test.docx",
  extra = {},
) {
  return new Request("http://localhost/api/v1/conversions", {
    method: "POST",
    headers: {
      "content-type": "application/octet-stream",
      "x-convx-filename": encodeURIComponent(name),
      ...extra,
    },
    body: bytes,
  });
}
async function isolated(t, options = {}) {
  const parent = await fs.mkdtemp(path.join(os.tmpdir(), "convx-node-"));
  const service = createRuntime({
    project,
    root: path.join(parent, "owned"),
    ...options,
  });
  t.after(async () => {
    await service.close();
    assert(
      path.resolve(parent).startsWith(path.resolve(os.tmpdir()) + path.sep),
    );
    await fs.rm(parent, { recursive: true });
  });
  return service;
}
async function terminal(service, id) {
  for (let n = 0; n < 7000; n++) {
    const record = await service.status(id);
    if (["failed", "blocked", "completed"].includes(record.state))
      return record;
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error(
    `Real Python process exceeded runtime deadline: ${JSON.stringify(await service.status(id))}`,
  );
}

test("real PDF upload reaches shared analysis and exposes only its verified PDF preview", async (t) => {
  const service = await isolated(t);
  const input = await fs.readFile(
    path.join(
      project,
      "tests/fixtures/06749LWD4_prelim_prospectus_automated.pdf",
    ),
  );
  const { jobs } = await service.create(upload(input, "independent-name.PDF"));
  const job = await terminal(service, jobs[0].id);
  assert.equal(
    job.state,
    "blocked",
    JSON.stringify(await service.validation(job.id)),
  );
  assert.equal(job.diagnostic_code, "PACKAGING_ENGINE_PENDING");
  const result = (await service.validation(job.id)).document_processing;
  assert.equal(result.input_preparation_complete, true);
  assert.equal(result.visual_reference.method, "direct_uploaded_pdf");
  assert.equal(result.revision_acceptance, null);
  const preview = await service.preview(job.id, "pdf");
  assert.deepEqual(Buffer.from(await preview.arrayBuffer()), input);
  assert.equal((await service.preview(job.id)).pages, 23);
  assert.equal((await service.preview(job.id)).available_pages.htm.length, 23);
  const screen = await service.preview(job.id, "htm");
  assert.equal(screen.headers.get("Content-Type"), "image/png");
  const generatedPath = path.join(
    service.root,
    job.id,
    result.workspace,
    "standard",
    result.html_generation.filename,
  );
  const originalHtml = await fs.readFile(generatedPath);
  await fs.appendFile(generatedPath, "changed");
  await assert.rejects(service.preview(job.id, "htm"));
  await fs.writeFile(generatedPath, originalHtml);
  await assert.rejects(service.download(job.id));
  await fs.appendFile(path.join(service.root, job.id, "source.pdf"), "changed");
  await assert.rejects(service.preview(job.id, "pdf"));
});
test("real Python admission fails unsafe content without a broker or database", async (t) => {
  const service = await isolated(t);
  const { jobs } = await service.create(upload());
  const job = await terminal(service, jobs[0].id);
  assert.equal(job.state, "failed");
  assert.equal(job.diagnostic_code, "INVALID_DOCX");
  assert.equal(job.download_available, false);
  const report = await service.validation(job.id);
  assert.equal(report.complete, false);
  assert.equal(report.diagnostics[0].code, "INVALID_DOCX");
  await assert.rejects(service.download(job.id), (e) => e.status === 409);
  await service.remove(job.id);
  await assert.rejects(service.status(job.id), (e) => e.status === 404);
});
test("stream and declared byte limits reject uploads and roll back private files", async (t) => {
  const service = await isolated(t, { maxBytes: 1024 });
  await assert.rejects(
    service.create(upload(Buffer.alloc(1025))),
    (e) => e.status === 413,
  );
  await assert.rejects(
    service.create(
      upload(Buffer.alloc(1), "test.docx", { "content-length": "1025" }),
    ),
    (e) => e.status === 413,
  );
  await assert.rejects(
    service.create(upload(Buffer.alloc(0))),
    (e) => e.code === "EMPTY_FILE",
  );
  assert.deepEqual(
    (await fs.readdir(service.root)).filter((name) => !name.startsWith(".")),
    [],
  );
});
test("filenames and mutating origins cannot escape the internal application", () => {
  for (const name of ["../x.docx", "a.exe", ".docx", "x.docx\n", "C:\\x.docx"])
    assert.throws(() => safeName(name));
  assert.equal(safeName("Résumé.docx"), "Résumé.docx");
  assert.throws(
    () =>
      originCheck(
        upload(undefined, "test.docx", { origin: "http://evil.example" }),
      ),
    (e) => e.status === 403,
  );
  assert.doesNotThrow(() =>
    originCheck(upload(undefined, "test.docx", { origin: "http://localhost" })),
  );
});
test("unknown IDs and filesystem traversal never reveal private files", async (t) => {
  const service = await isolated(t);
  for (const id of [
    "../../secret",
    "not-an-id",
    "00000000-0000-4000-8000-000000000000",
  ])
    await assert.rejects(service.status(id), (e) => e.status === 404);
});
test("queued cancellation is immediately revoked and never becomes completed", async (t) => {
  const service = await isolated(t);
  const one = (await service.create(upload())).jobs[0];
  const two = (await service.create(upload())).jobs[0];
  await service.remove(two.id);
  await assert.rejects(service.status(two.id), (e) => e.status === 404);
  assert.equal((await terminal(service, one.id)).state, "failed");
});
test("restart marks an interrupted job failed without fake progress", async (t) => {
  const first = await isolated(t);
  const created = (await first.create(upload())).jobs[0];
  await terminal(first, created.id);
  const file = path.join(first.root, created.id, "meta.json");
  const record = JSON.parse(await fs.readFile(file));
  await fs.writeFile(file, JSON.stringify({ ...record, state: "running" }));
  const restarted = createRuntime({ project, root: first.root });
  t.after(() => restarted.close());
  assert.equal(
    (await restarted.status(created.id)).diagnostic_code,
    "PROCESS_INTERRUPTED",
  );
});
test("expired captures and invalid proof flags never grant downloads", async (t) => {
  const service = await isolated(t);
  const job = (await service.create(upload())).jobs[0];
  await terminal(service, job.id);
  const file = path.join(service.root, job.id, "meta.json");
  const record = JSON.parse(await fs.readFile(file));
  await fs.writeFile(
    file,
    JSON.stringify({ ...record, expires_at: new Date(0).toISOString() }),
  );
  await assert.rejects(service.download(job.id), (e) => e.status === 410);
  await service.cleanup();
  await assert.rejects(service.status(job.id), (e) => e.status === 404);
});

function independentPdf() {
  const content =
    "BT /F1 12 Tf 40 500 Td (Independent EDGAR disclosure 123.45) Tj ET";
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 600] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  for (const [i, value] of objects.entries()) {
    offsets.push(Buffer.byteLength(pdf));
    pdf += `${i + 1} 0 obj\n${value}\nendobj\n`;
  }
  const start = Buffer.byteLength(pdf);
  pdf += `xref\n0 6\n0000000000 65535 f \n${offsets
    .slice(1)
    .map((n) => String(n).padStart(10, "0") + " 00000 n \n")
    .join("")}trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${start}\n%%EOF\n`;
  return Buffer.from(pdf);
}

test("real EDGAR mode stays bound through retry and verified previews", async (t) => {
  const service = await isolated(t);
  const previousCache = process.env.PLAYWRIGHT_BROWSERS_PATH;
  const restoreCache = () => {
    if (previousCache === undefined)
      delete process.env.PLAYWRIGHT_BROWSERS_PATH;
    else process.env.PLAYWRIGHT_BROWSERS_PATH = previousCache;
  };
  t.after(restoreCache);
  process.env.PLAYWRIGHT_BROWSERS_PATH = path.join(
    service.root,
    "missing-browser",
  );
  await assert.rejects(
    service.create(
      upload(independentPdf(), "test.pdf", { "x-convx-mode": "unsafe" }),
    ),
    (e) => e.code === "INVALID_MODE",
  );
  const created = (
    await service.create(
      upload(independentPdf(), "financial report.pdf", {
        "x-convx-mode": "edgar",
      }),
    )
  ).jobs[0];
  assert.equal(created.mode, "edgar");
  assert.equal(
    (await terminal(service, created.id)).diagnostic_code,
    "EDGAR_BROWSER_UNAVAILABLE",
  );
  restoreCache();
  await service.resume(created.id);
  const job = await terminal(service, created.id);
  const report = (await service.validation(job.id)).document_processing;
  assert.equal(
    job.diagnostic_code,
    "PACKAGING_ENGINE_PENDING",
    JSON.stringify(report),
  );
  assert.equal(report.mode, "edgar");
  assert.equal(report.sec_validation.passed, true);
  assert.equal(report.sec_validation.strict_passed, false);
  assert.equal(report.sec_validation.sec_acceptance_confirmed, false);
  assert.equal((await service.preview(job.id)).available_pages.htm.length, 1);
  const screen = await service.preview(job.id, "htm");
  assert.equal(screen.headers.get("Content-Type"), "image/png");
  const file = path.join(
    service.root,
    job.id,
    report.workspace,
    "edgar",
    report.html_generation.filename,
  );
  const original = await fs.readFile(file);
  await fs.appendFile(file, "changed");
  await assert.rejects(service.preview(job.id, "htm"));
  await fs.writeFile(file, original);
  await assert.rejects(service.download(job.id));
  await assert.rejects(
    service.resume(job.id),
    (e) => e.code === "JOB_NOT_RESUMABLE",
  );
});
