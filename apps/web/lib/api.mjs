export class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}
export async function request(path, options = {}) {
  const response = await fetch(`/api/v1/conversions${path}`, {
    ...options,
    headers: options.headers,
    cache: "no-store",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(
      data.error?.message || "Request could not be completed.",
      response.status,
      data.error?.code,
    );
  }
  return response;
}
export async function json(path, options) {
  return (await request(path, options)).json();
}
export async function upload(files, onProgress, signal) {
  const jobs = [],
    errors = [];
  for (let index = 0; index < files.length; index++) {
    const file = files[index];
    try {
      const result = await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const abort = () => xhr.abort();
        xhr.open("POST", "/api/v1/conversions");
        xhr.timeout = 180000;
        xhr.setRequestHeader("Content-Type", "application/octet-stream");
        xhr.setRequestHeader("X-Convx-Filename", encodeURIComponent(file.name));
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable)
            onProgress(
              Math.round((100 * (index + e.loaded / e.total)) / files.length),
            );
        };
        const cleanup = () => signal?.removeEventListener("abort", abort);
        xhr.onload = () => {
          cleanup();
          try {
            const data = JSON.parse(xhr.responseText);
            if (xhr.status >= 200 && xhr.status < 300) resolve(data);
            else
              reject(
                new ApiError(
                  data.error?.message || "Upload failed",
                  xhr.status,
                  data.error?.code,
                ),
              );
          } catch (e) {
            reject(
              e instanceof ApiError
                ? e
                : new ApiError("Invalid server response", xhr.status),
            );
          }
        };
        xhr.onerror = () => {
          cleanup();
          reject(new ApiError("Upload connection lost", 0));
        };
        xhr.ontimeout = () => {
          cleanup();
          reject(new ApiError("Upload timed out", 408));
        };
        xhr.onabort = () => {
          cleanup();
          reject(new DOMException("Upload cancelled", "AbortError"));
        };
        if (signal?.aborted) {
          reject(new DOMException("Upload cancelled", "AbortError"));
          return;
        }
        signal?.addEventListener("abort", abort, { once: true });
        xhr.send(file);
      });
      jobs.push(...result.jobs);
    } catch (e) {
      if (e.name === "AbortError") throw e;
      errors.push({ filename: file.name, message: e.message, index });
    }
  }
  return { jobs, errors, replayed: false };
}
