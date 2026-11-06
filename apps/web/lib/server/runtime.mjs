import { promises as fs, writeFileSync } from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { spawn } from "node:child_process";

const ID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const END = new Set(["failed", "blocked", "completed", "cancelled", "expired"]);
const digest = (data) => crypto.createHash("sha256").update(data).digest("hex");
export class Failure extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}
const fail = (status, code, message) => {
  throw new Failure(status, code, message);
};
export const noStore = {
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
};

export function originCheck(request) {
  const origin = request.headers.get("origin");
  const expected = new URL(request.url);
  expected.host = request.headers.get("host") || expected.host;
  if (!["localhost", "127.0.0.1", "[::1]"].includes(expected.hostname))
    fail(
      403,
      "HOST_REJECTED",
      "This local application requires a loopback host",
    );
  if (
    request.headers.get("sec-fetch-site") === "cross-site" ||
    (origin && origin !== expected.origin)
  )
    fail(403, "ORIGIN_REJECTED", "Use the application's own origin");
}

export function safeName(value) {
  if (
    !value ||
    Buffer.byteLength(value, "utf8") > 240 ||
    value.startsWith(".") ||
    /[\x00-\x1f\x7f/\\:<>"|?*]/.test(value) ||
    /[ .]$/.test(value)
  )
    fail(422, "INVALID_FILENAME", "Use a safe plain document filename");
  if (!/^.+\.docx$/i.test(value))
    fail(
      415,
      "UNSUPPORTED_FILE_TYPE",
      "This implementation stage accepts DOCX only",
    );
  return value;
}

export function createRuntime(options = {}) {
  const project = path.resolve(
    /* turbopackIgnore: true */
    options.project ||
      process.env.CONVX_PROJECT_ROOT ||
      path.resolve(/* turbopackIgnore: true */ process.cwd(), "../.."),
  );
  const root = path.resolve(
    /* turbopackIgnore: true */
    options.root ||
      process.env.CONVX_TEMP_ROOT ||
      path.join(/* turbopackIgnore: true */ project, "var/conversions"),
  );
  const python =
    options.python ||
    process.env.CONVX_PYTHON ||
    path.join(
      /* turbopackIgnore: true */
      project,
      ".venv",
      process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
    );
  const maxBytes = options.maxBytes || 20 * 1024 * 1024;
  const concurrency = 1,
    maxPending = 10,
    retention = options.retention || 86400_000;
  const instance = crypto.randomUUID(),
    active = new Map(),
    queue = [],
    mutations = new Map();
  function locked(id, action) {
    const result = (mutations.get(id) || Promise.resolve()).then(action);
    const tail = result
      .catch(() => {})
      .finally(() => {
        if (mutations.get(id) === tail) mutations.delete(id);
      });
    mutations.set(id, tail);
    return result;
  }
  let initialized,
    stopping = false,
    uploads = 0,
    cleanupTimer;

  async function init() {
    if (!initialized)
      initialized = (async () => {
        await fs.mkdir(root, { recursive: true, mode: 0o700 });
        if ((await fs.lstat(root)).isSymbolicLink())
          fail(500, "STORAGE_UNSAFE", "Private storage is linked");
        const marker = path.join(
          /* turbopackIgnore: true */ root,
          ".convx-runtime",
        );
        try {
          await fs.writeFile(marker, "convx-runtime-v1\n", {
            flag: "wx",
            mode: 0o600,
          });
        } catch (error) {
          if (
            error.code !== "EEXIST" ||
            (await fs.readFile(marker, "utf8")) !== "convx-runtime-v1\n"
          )
            throw error;
        }
        await fs.access(python);
        cleanupTimer = setInterval(() => cleanup().catch(() => {}), 60_000);
        cleanupTimer.unref();
      })();
    await initialized;
  }
  function directory(id) {
    if (!ID.test(id)) fail(404, "JOB_NOT_FOUND", "Job not found");
    return path.join(/* turbopackIgnore: true */ root, id);
  }
  async function owned(id) {
    await init();
    const dir = directory(id);
    try {
      if (
        (await fs.lstat(dir)).isSymbolicLink() ||
        path.relative(await fs.realpath(root), await fs.realpath(dir)) !== id
      )
        fail(404, "JOB_NOT_FOUND", "Job not found");
    } catch {
      fail(404, "JOB_NOT_FOUND", "Job not found");
    }
    return dir;
  }
  async function read(file, limit = 8 * 1024 * 1024) {
    const stat = await fs.lstat(file);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size > limit)
      throw new Error("Unsafe bounded artifact");
    const data = await fs.readFile(file);
    if (data.length > limit) throw new Error("Artifact exceeds budget");
    return data;
  }
  async function json(file) {
    return JSON.parse(await read(file));
  }
  async function write(file, value) {
    const part = `${file}.${crypto.randomUUID()}.part`;
    try {
      await fs.writeFile(part, JSON.stringify(value), {
        flag: "wx",
        mode: 0o600,
      });
      await fs.rename(part, file);
    } finally {
      await fs.unlink(part).catch(() => {});
    }
  }
  async function meta(id) {
    const dir = await owned(id);
    let record;
    try {
      record = await json(
        path.join(/* turbopackIgnore: true */ dir, "meta.json"),
      );
    } catch {
      fail(404, "JOB_NOT_FOUND", "Job not found");
    }
    if (record.id !== id || record.deleted)
      fail(404, "JOB_NOT_FOUND", "Job not found");
    if (Date.now() >= Date.parse(record.expires_at))
      return {
        ...record,
        state: "expired",
        stage: "expired",
        download_available: false,
      };
    if (!END.has(record.state) && record.instance !== instance) {
      record = {
        ...record,
        state: "failed",
        stage: "processing",
        diagnostic_code: "PROCESS_INTERRUPTED",
        download_available: false,
        updated_at: new Date().toISOString(),
        version: Date.now(),
      };
      await write(
        path.join(/* turbopackIgnore: true */ dir, "meta.json"),
        record,
      );
    }
    return record;
  }
  async function cleanup() {
    await init();
    for (const entry of await fs.readdir(root, { withFileTypes: true })) {
      if (
        !ID.test(entry.name) ||
        !entry.isDirectory() ||
        entry.isSymbolicLink() ||
        active.has(entry.name) ||
        queue.includes(entry.name)
      )
        continue;
      try {
        const dir = await owned(entry.name),
          record = await json(
            path.join(/* turbopackIgnore: true */ dir, "meta.json"),
          );
        if (
          record.id === entry.name &&
          (record.deleted || Date.now() >= Date.parse(record.expires_at))
        ) {
          // owned() verifies this resolved UUID child before any recursive removal.
          await fs.rm(dir, { recursive: true });
        }
      } catch {
        /* Preserve unknown/corrupt directories; never guess ownership. */
      }
    }
  }
  async function report(id) {
    const dir = await owned(id),
      record = await meta(id);
    try {
      const value = await json(
        path.join(/* turbopackIgnore: true */ dir, "result.json"),
      );
      if (value.source_sha256 && value.source_sha256 !== record.source_sha256)
        return null;
      return value;
    } catch {
      return null;
    }
  }
  function pump() {
    if (stopping || active.size >= concurrency || !queue.length) return;
    const id = queue.shift();
    const promise = launch(id)
      .catch(() => {})
      .finally(() => {
        active.delete(id);
        pump();
      });
    active.set(id, { promise, child: null });
  }
  async function launch(id) {
    const dir = await owned(id);
    const claimed = await locked(id, async () => {
      const record = await meta(id);
      if (record.state !== "queued") return false;
      await write(path.join(/* turbopackIgnore: true */ dir, "meta.json"), {
        ...record,
        state: "running",
        stage: "validating",
        attempts: record.attempts + 1,
        version: Date.now(),
        updated_at: new Date().toISOString(),
      });
      return true;
    });
    if (!claimed) return;
    let timer;
    let exitCode;
    await new Promise((resolve) => {
      const child = spawn(
        /* turbopackIgnore: true */
        python,
        [
          "-m",
          "converter.runtime",
          path.join(/* turbopackIgnore: true */ dir, "request.json"),
        ],
        {
          cwd: project,
          windowsHide: true,
          shell: false,
          stdio: ["ignore", "ignore", "ignore"],
          env: {
            ...process.env,
            PYTHONPATH: path.join(
              /* turbopackIgnore: true */ project,
              "packages",
            ),
            PYTHONUNBUFFERED: "1",
          },
        },
      );
      active.get(id).child = child;
      const stop = () =>
        fs
          .writeFile(
            path.join(/* turbopackIgnore: true */ dir, "cancelled"),
            "cancel",
            { mode: 0o600 },
          )
          .catch(() => {});
      timer = setTimeout(stop, 330_000);
      timer.unref();
      child.once("error", resolve);
      child.once("exit", (code) => {
        exitCode = code;
        resolve();
      });
    });
    clearTimeout(timer);
    await locked(id, async () => {
      const current = await meta(id);
      if (
        current.deleted ||
        current.state === "cancelled" ||
        current.state === "expired"
      )
        return;
      const result = await report(id);
      // Python's retained pipeline writes real proof; final download independently audits it.
      const state =
        exitCode === 0 &&
        result?.status === "packaged" &&
        result?.final_conversion_complete === true
          ? "completed"
          : result?.status === "blocked"
            ? "blocked"
            : "failed";
      await write(path.join(/* turbopackIgnore: true */ dir, "meta.json"), {
        ...current,
        state,
        stage:
          result?.diagnostics?.[0]?.stage ||
          (state === "completed" ? "completed" : "processing"),
        diagnostic_code:
          result?.diagnostics?.[0]?.code ||
          (state === "completed" ? null : "CONVERSION_PROCESS_FAILED"),
        download_available: state === "completed",
        version: Date.now(),
        updated_at: new Date().toISOString(),
      });
    });
  }
  async function create(request) {
    await init();
    originCheck(request);
    if (stopping)
      fail(503, "SERVICE_STOPPING", "Document processing is stopping");
    if (uploads + active.size + queue.length >= maxPending)
      fail(429, "CONCURRENCY_LIMIT", "Too many pending documents");
    uploads++;
    try {
      return await receiveUpload(request);
    } finally {
      uploads--;
    }
  }
  async function receiveUpload(request) {
    await init();
    originCheck(request);
    await cleanup();
    if (queue.length + active.size >= maxPending)
      fail(
        429,
        "CONCURRENCY_LIMIT",
        "Too many pending documents; wait for the current conversion",
      );
    if (request.headers.get("content-type") !== "application/octet-stream")
      fail(415, "BINARY_UPLOAD_REQUIRED", "Upload document bytes");
    let name;
    try {
      name = safeName(
        decodeURIComponent(request.headers.get("x-convx-filename") || ""),
      );
    } catch (error) {
      if (error instanceof Failure) throw error;
      fail(422, "INVALID_FILENAME", "Invalid document name");
    }
    const declared = Number(request.headers.get("content-length"));
    if (declared > maxBytes)
      fail(413, "FILE_TOO_LARGE", "Document exceeds the upload limit");
    if ((await fs.readdir(root)).filter((name) => ID.test(name)).length >= 100)
      fail(
        429,
        "STORAGE_LIMIT",
        "Private temporary storage is full; remove old conversions",
      );
    const id = crypto.randomUUID(),
      dir = directory(id);
    await fs.mkdir(dir, { mode: 0o700 });
    let count = 0,
      handle,
      reader,
      timer;
    const hash = crypto.createHash("sha256");
    try {
      await write(path.join(dir, "meta.json"), {
        id,
        instance,
        state: "uploading",
        stage: "uploaded",
        attempts: 0,
        version: Date.now(),
        expires_at: new Date(Date.now() + 120000).toISOString(),
      });
      handle = await fs.open(
        path.join(/* turbopackIgnore: true */ dir, "source.docx"),
        "wx",
        0o600,
      );
      if (!request.body) fail(422, "EMPTY_FILE", "Document is empty");
      reader = request.body.getReader();
      const timeout = new Promise((_, reject) => {
        timer = setTimeout(
          () => reject(new Failure(408, "UPLOAD_TIMEOUT", "Upload timed out")),
          120000,
        );
        timer.unref();
      });
      for (;;) {
        const { value, done } = await Promise.race([reader.read(), timeout]);
        if (done) break;
        count += value.length;
        if (count > maxBytes)
          fail(413, "FILE_TOO_LARGE", "Document exceeds the upload limit");
        hash.update(value);
        let offset = 0;
        while (offset < value.length) {
          const part = await handle.write(value, offset, value.length - offset);
          if (!part.bytesWritten) throw new Error("Incomplete write");
          offset += part.bytesWritten;
        }
      }
      if (!count) fail(422, "EMPTY_FILE", "Document is empty");
      await handle.sync();
      await handle.close();
      handle = null;
      const now = new Date().toISOString();
      const record = {
        id,
        instance,
        original_filename: name,
        source_sha256: hash.digest("hex"),
        source_bytes: count,
        state: "queued",
        stage: "uploaded",
        version: Date.now(),
        attempts: 0,
        created_at: now,
        updated_at: now,
        expires_at: new Date(Date.now() + retention).toISOString(),
        diagnostic_code: null,
        download_available: false,
      };
      await write(path.join(/* turbopackIgnore: true */ dir, "request.json"), {
        original_filename: name,
        limits: { max_upload_bytes: maxBytes },
        attempt: 1,
      });
      await write(
        path.join(/* turbopackIgnore: true */ dir, "meta.json"),
        record,
      );
      queue.push(id);
      pump();
      return { jobs: [record], errors: [], replayed: false };
    } catch (error) {
      await handle?.close();
      await reader?.cancel().catch(() => {});
      // Newly created opaque directory is checked again before recursive rollback.
      await owned(id);
      await fs.rm(dir, { recursive: true });
      throw error;
    } finally {
      clearTimeout(timer);
      reader?.releaseLock();
    }
  }
  async function status(id) {
    const record = await meta(id);
    if (record.state === "running") {
      try {
        const dir = await owned(id),
          file = path.join(/* turbopackIgnore: true */ dir, "progress.json"),
          progress = await json(file);
        const version = Math.floor((await fs.stat(file)).mtimeMs);
        return {
          ...record,
          stage: progress.stage,
          version: Math.max(record.version, version),
        };
      } catch {
        /* No fake processing percentage when progress is absent. */
      }
    }
    return record;
  }
  async function validation(id) {
    const record = await meta(id);
    if (record.state === "expired")
      fail(410, "JOB_EXPIRED", "Temporary retention has expired");
    const processing = await report(id);
    return {
      id,
      complete: record.state === "completed" && record.download_available,
      sec_compliance_passed: processing?.sec_validation?.strict_passed === true,
      fidelity_passed: processing?.visual_validation?.strict_passed === true,
      document_processing: processing,
      diagnostics:
        processing?.diagnostics ||
        (record.diagnostic_code
          ? [
              {
                code: record.diagnostic_code,
                description: "Processing did not complete",
              },
            ]
          : []),
    };
  }
  async function remove(id) {
    const dir = await owned(id),
      record = await meta(id);
    await fs.writeFile(
      path.join(/* turbopackIgnore: true */ dir, "cancelled"),
      "cancel",
      { mode: 0o600 },
    );
    await write(path.join(/* turbopackIgnore: true */ dir, "meta.json"), {
      ...record,
      deleted: true,
      state: "cancelled",
      download_available: false,
    });
    const index = queue.indexOf(id);
    if (index >= 0) queue.splice(index, 1);
    if (!active.has(id)) await cleanup();
    return { id, state: "cancelled", cleanup_pending: active.has(id) };
  }
  async function artifactPath(dir, relative) {
    if (
      typeof relative !== "string" ||
      relative.includes("\\") ||
      relative.includes(":") ||
      path.isAbsolute(relative) ||
      relative.split("/").some((part) => ["", ".", ".."].includes(part))
    )
      throw new Error("Unsafe artifact path");
    let candidate = dir;
    for (const part of relative.split("/")) {
      candidate = path.join(/* turbopackIgnore: true */ candidate, part);
      if ((await fs.lstat(candidate)).isSymbolicLink())
        throw new Error("Linked artifact");
    }
    if (path.relative(dir, await fs.realpath(candidate)).startsWith(".."))
      throw new Error("Artifact outside conversion");
    return candidate;
  }
  async function preview(id, kind, page = 1) {
    const record = await meta(id),
      dir = await owned(id);
    if (record.state === "expired")
      fail(410, "JOB_EXPIRED", "Temporary retention has expired");
    if (!END.has(record.state))
      fail(
        409,
        "PREVIEW_NOT_AVAILABLE",
        "Preview is available after processing stops",
      );
    try {
      const result = await report(id),
        proof = result?.pdf_validation;
      if (
        !result?.source_unchanged ||
        !proof?.candidate_sha256 ||
        digest(
          await read(
            path.join(/* turbopackIgnore: true */ dir, "source.docx"),
            maxBytes,
          ),
        ) !== record.source_sha256
      )
        throw new Error("Source changed");
      const pdf = await artifactPath(
        dir,
        `${result.workspace}/${result.generated_pdf_artifact}`,
      );
      const data = await read(pdf, 64 * 1024 * 1024);
      if (
        digest(data) !== proof.candidate_sha256 ||
        !data.subarray(0, 5).equals(Buffer.from("%PDF-"))
      )
        throw new Error("PDF changed");
      const pages = proof.page_count;
      if (!Number.isInteger(pages) || pages < 1 || pages > 2000)
        throw new Error("No valid pages");
      const available_pages = { htm: [], overlay: [], difference: [] };
      const suffix = {
        htm: "screen",
        overlay: "overlay",
        difference: "print-diff",
      };
      for (const option of Object.keys(suffix))
        for (let n = 1; n <= pages; n++)
          if (
            result.visual_validation?.artifacts?.includes(
              `page${String(n).padStart(4, "0")}.${suffix[option]}.png`,
            )
          )
            available_pages[option].push(n);
      if (!kind)
        return {
          pages,
          pdf_available: true,
          available_pages,
          capture_dpi: result.visual_validation?.policy?.dpi || 96,
          diagnostic_only: true,
          conversion_eligible: false,
        };
      if (!Number.isInteger(page) || page < 1 || page > pages)
        fail(422, "PREVIEW_PAGE_INVALID", "Page is outside this document");
      if (kind === "pdf")
        return new Response(data, {
          headers: { ...noStore, "Content-Type": "application/pdf" },
        });
      if (!suffix[kind] || !available_pages[kind].includes(page))
        throw new Error("Capture unavailable");
      const image = await read(
        await artifactPath(
          dir,
          `${result.workspace}/visual/page${String(page).padStart(4, "0")}.${suffix[kind]}.png`,
        ),
        64 * 1024 * 1024,
      );
      if (
        !image
          .subarray(0, 8)
          .equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) ||
        image.length < 24 ||
        image.readUInt32BE(16) * image.readUInt32BE(20) > 16_000_000
      )
        throw new Error("Invalid capture");
      return new Response(image, {
        headers: { ...noStore, "Content-Type": "image/png" },
      });
    } catch (error) {
      if (error instanceof Failure) throw error;
      fail(
        409,
        "PREVIEW_NOT_AVAILABLE",
        "Current diagnostic preview is unavailable",
      );
    }
  }
  async function close() {
    stopping = true;
    clearInterval(cleanupTimer);
    for (const id of active.keys())
      await fs
        .writeFile(
          path.join(/* turbopackIgnore: true */ directory(id), "cancelled"),
          "cancel",
        )
        .catch(() => {});
    await Promise.allSettled(
      [...active.values()].map((value) => value.promise),
    );
  }
  function cancelOnExit() {
    for (const id of active.keys()) {
      try {
        writeFileSync(
          path.join(/* turbopackIgnore: true */ directory(id), "cancelled"),
          "cancel",
          { mode: 0o600 },
        );
      } catch {
        /* Child resource deadline is the final fallback. */
      }
    }
  }
  async function resume(id) {
    const record = await meta(id),
      dir = await owned(id);
    if (
      record.state !== "blocked" ||
      record.attempts >= 3 ||
      ![
        "PDF_REFERENCE_REQUIRED",
        "PDF_RENDERER_UNAVAILABLE",
        "VISUAL_BROWSER_UNAVAILABLE",
      ].includes(record.diagnostic_code)
    )
      fail(409, "JOB_NOT_RESUMABLE", "This document cannot be retried");
    if (queue.length + active.size >= maxPending)
      fail(429, "CONCURRENCY_LIMIT", "Too many pending documents");
    await fs
      .unlink(path.join(/* turbopackIgnore: true */ dir, "result.json"))
      .catch(() => {});
    await fs
      .unlink(path.join(/* turbopackIgnore: true */ dir, "progress.json"))
      .catch(() => {});
    await write(path.join(/* turbopackIgnore: true */ dir, "request.json"), {
      original_filename: record.original_filename,
      limits: { max_upload_bytes: maxBytes },
      attempt: record.attempts + 1,
    });
    await write(path.join(/* turbopackIgnore: true */ dir, "meta.json"), {
      ...record,
      instance,
      state: "queued",
      stage: "uploaded",
      diagnostic_code: null,
      version: Date.now(),
      updated_at: new Date().toISOString(),
    });
    queue.push(id);
    pump();
    return { id, state: "queued" };
  }
  async function download(id) {
    const record = await meta(id),
      dir = await owned(id),
      value = await report(id);
    if (record.state === "expired")
      fail(410, "JOB_EXPIRED", "Temporary retention expired");
    if (
      record.state !== "completed" ||
      !record.download_available ||
      !value?.workspace
    )
      fail(409, "ARTIFACT_NOT_AVAILABLE", "No qualified archive is available");
    const data = await read(
      await artifactPath(dir, `${value.workspace}/package/result.zip`),
      128 * 1024 * 1024,
    );
    const audit = await new Promise((resolve, reject) => {
      const child = spawn(
        /* turbopackIgnore: true */
        python,
        [
          "-m",
          "converter.runtime",
          "--audit",
          path.join(/* turbopackIgnore: true */ dir, "request.json"),
        ],
        {
          cwd: project,
          windowsHide: true,
          shell: false,
          stdio: ["ignore", "pipe", "ignore"],
          env: {
            ...process.env,
            PYTHONPATH: path.join(
              /* turbopackIgnore: true */ project,
              "packages",
            ),
          },
        },
      );
      let output = "";
      const timer = setTimeout(() => {
        child.kill();
        reject(new Error("Audit timed out"));
      }, 65000);
      timer.unref();
      child.stdout.on("data", (chunk) => {
        output += chunk;
        if (output.length > 4096) child.kill();
      });
      child.once("error", (error) => {
        clearTimeout(timer);
        reject(error);
      });
      child.once("exit", (code) => {
        clearTimeout(timer);
        try {
          if (code !== 0) throw new Error("Invalid archive");
          resolve(JSON.parse(output));
        } catch (error) {
          reject(error);
        }
      });
    }).catch(() =>
      fail(
        409,
        "PACKAGE_VALIDATION_FAILED",
        "Current archive or evidence did not pass checks",
      ),
    );
    const current = await meta(id);
    if (
      current.state !== "completed" ||
      current.version !== record.version ||
      digest(data) !== audit.sha256 ||
      data.length !== audit.bytes
    )
      fail(
        409,
        "PACKAGE_VALIDATION_FAILED",
        "Archive changed during validation",
      );
    return new Response(data, {
      headers: {
        ...noStore,
        "Content-Type": "application/zip",
        "Content-Length": String(data.length),
        "Content-Disposition": `attachment; filename*=utf-8''${encodeURIComponent(audit.filename)}`,
      },
    });
  }
  return {
    init,
    create,
    status,
    validation,
    remove: (id) => locked(id, () => remove(id)),
    preview,
    resume: (id) => locked(id, () => resume(id)),
    download,
    close,
    cancelOnExit,
    cleanup,
    root,
    python,
    project,
    limits: {
      max_upload_bytes: maxBytes,
      max_request_bytes: maxBytes * 10,
      max_batch_files: 10,
      auth_mode: "internal",
    },
  };
}

const symbol = Symbol.for("convx.internal-runtime");
export function runtime() {
  if (!globalThis[symbol]) {
    globalThis[symbol] = createRuntime();
    process.once("exit", () => globalThis[symbol].cancelOnExit());
  }
  return globalThis[symbol];
}

export async function respond(action) {
  try {
    const value = await action();
    return value instanceof Response
      ? value
      : Response.json(value, { headers: noStore });
  } catch (error) {
    return Response.json(
      {
        error: {
          code: error instanceof Failure ? error.code : "REQUEST_FAILED",
          message:
            error instanceof Failure
              ? error.message
              : "Request could not be completed",
        },
      },
      {
        status: error instanceof Failure ? error.status : 500,
        headers: noStore,
      },
    );
  }
}
