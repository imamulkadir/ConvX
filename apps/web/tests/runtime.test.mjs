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
  for (let n = 0; n < 1200; n++) {
    const record = await service.status(id);
    if (["failed", "blocked", "completed"].includes(record.state))
      return record;
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error("Real Python process did not finish");
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
  assert.equal(job.diagnostic_code, "MODE_RENDERER_PENDING");
  const result = (await service.validation(job.id)).document_processing;
  assert.equal(result.input_preparation_complete, true);
  assert.equal(result.visual_reference.method, "direct_uploaded_pdf");
  assert.equal(result.revision_acceptance, null);
  const preview = await service.preview(job.id, "pdf");
  assert.deepEqual(Buffer.from(await preview.arrayBuffer()), input);
  assert.equal((await service.preview(job.id)).pages, 23);
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
