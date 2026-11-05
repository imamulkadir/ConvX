export class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}
export function headers(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}
export async function request(path, token, options = {}) {
  const response = await fetch(`/api/v1/conversions${path}`, {
    ...options,
    headers: { ...headers(token), ...options.headers },
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
export async function json(path, token, options) {
  return (await request(path, token, options)).json();
}
export function upload(files, token, onProgress, signal) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const abort = () => xhr.abort();
    xhr.open("POST", "/api/v1/conversions");
    xhr.timeout = 180000;
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.setRequestHeader("Idempotency-Key", crypto.randomUUID());
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable)
        onProgress(Math.round((100 * e.loaded) / e.total));
    };
    xhr.onload = () => {
      signal?.removeEventListener("abort", abort);
      let data;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        reject(new ApiError("Invalid upload response.", xhr.status));
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data);
      else
        reject(
          new ApiError(
            data.error?.message || "Upload failed.",
            xhr.status,
            data.error?.code,
          ),
        );
    };
    xhr.onerror = () => {
      signal?.removeEventListener("abort", abort);
      reject(
        new ApiError(
          "Connection lost. Check the workspace before uploading again.",
          0,
        ),
      );
    };
    xhr.ontimeout = () => {
      signal?.removeEventListener("abort", abort);
      reject(
        new ApiError(
          "Upload timed out. Check the workspace before uploading again.",
          0,
        ),
      );
    };
    xhr.onabort = () => {
      signal?.removeEventListener("abort", abort);
      reject(new DOMException("Upload cancelled", "AbortError"));
    };
    const body = new FormData();
    files.forEach((file) => body.append("files", file));
    signal?.addEventListener("abort", abort, { once: true });
    if (signal?.aborted) {
      reject(new DOMException("Upload cancelled", "AbortError"));
      return;
    }
    xhr.send(body);
  });
}
