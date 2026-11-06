"use client";
import { useEffect, useRef, useState } from "react";
import { json, request, upload } from "../lib/api.mjs";
import { downloadName, terminal } from "../lib/jobs.mjs";
const STORAGE = "convx-current-job";
function remember(id) {
  try {
    if (id) sessionStorage.setItem(STORAGE, id);
    else {
      sessionStorage.removeItem(STORAGE);
      sessionStorage.removeItem("convx-jobs");
    }
  } catch {
    /* Conversion works without browser storage. */
  }
}
export default function useConversion() {
  const [session, setSession] = useState(null),
    [job, setJob] = useState(null),
    [report, setReport] = useState(null);
  const [error, setError] = useState(""),
    [progress, setProgress] = useState(null),
    [busy, setBusy] = useState(null);
  const [connection, setConnection] = useState(0);
  const lifecycle = useRef(null),
    pendingUpload = useRef(null);
  useEffect(() => {
    const controller = new AbortController();
    lifecycle.current = controller;
    (async () => {
      const limits = await json("/session", { signal: controller.signal });
      let id;
      try {
        id =
          sessionStorage.getItem(STORAGE) ||
          JSON.parse(sessionStorage.getItem("convx-jobs") || "[]")[0];
      } catch {
        /* Optional tab state. */
      }
      let restored = null;
      if (typeof id === "string" && /^[a-f0-9-]{36}$/.test(id)) {
        try {
          restored = await json(`/${id}`, { signal: controller.signal });
        } catch (e) {
          if (e.name === "AbortError") throw e;
          if ([404, 410].includes(e.status)) remember(null);
          else throw e;
        }
      }
      if (!controller.signal.aborted) {
        setJob(restored);
        setSession(limits);
        setError("");
        if (restored) remember(restored.id);
      }
    })().catch((e) => {
      if (!controller.signal.aborted)
        setError(
          e.message || "The converter is unavailable. Please try again.",
        );
    });
    return () => {
      controller.abort();
      pendingUpload.current?.abort();
    };
  }, [connection]);
  useEffect(() => {
    if (!job || terminal.has(job.state)) return;
    const controller = new AbortController();
    let timer;
    async function poll() {
      let delay = 1200;
      try {
        const fresh = await json(`/${job.id}`, { signal: controller.signal });
        if (controller.signal.aborted) return;
        setJob(fresh);
        setError("");
        if (terminal.has(fresh.state)) return;
      } catch (e) {
        if (controller.signal.aborted) return;
        if ([404, 410].includes(e.status)) {
          setJob({ ...job, state: "expired", download_available: false });
          return;
        }
        setError(
          "Connection interrupted. Status updates will retry automatically.",
        );
        delay = 5000;
      }
      timer = setTimeout(poll, delay);
    }
    timer = setTimeout(poll, 250);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [job?.id, job?.state]);
  useEffect(() => {
    setReport(null);
    if (!job || !terminal.has(job.state)) return;
    const controller = new AbortController();
    let timer;
    async function load() {
      try {
        const result = await json(`/${job.id}/validation`, {
          signal: controller.signal,
        });
        if (!controller.signal.aborted) {
          setReport(result);
          setError("");
        }
      } catch (e) {
        if (controller.signal.aborted || [404, 410].includes(e.status)) return;
        setError("Conversion details are unavailable. Reconnecting…");
        timer = setTimeout(load, 5000);
      }
    }
    load();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [job?.id, job?.state]);
  async function convert(file, mode) {
    if (!session || job || busy) return;
    const controller = new AbortController();
    pendingUpload.current = controller;
    const stop = () => controller.abort();
    lifecycle.current.signal.addEventListener("abort", stop, { once: true });
    setBusy("upload");
    setProgress(0);
    setError("");
    try {
      const result = await upload([file], setProgress, controller.signal, mode);
      if (controller.signal.aborted) return;
      if (result.jobs.length !== 1)
        throw new Error(
          result.errors[0]?.message || "Upload failed. Please try again.",
        );
      setJob(result.jobs[0]);
      remember(result.jobs[0].id);
    } catch (e) {
      if (!controller.signal.aborted) setError(e.message);
    } finally {
      lifecycle.current?.signal.removeEventListener("abort", stop);
      pendingUpload.current = null;
      if (!lifecycle.current?.signal.aborted) {
        setBusy(null);
        setProgress(null);
      }
    }
  }
  async function reset() {
    if (busy) return false;
    setBusy("reset");
    setError("");
    try {
      if (job) {
        try {
          await json(`/${job.id}`, {
            method: "DELETE",
            signal: lifecycle.current.signal,
          });
        } catch (e) {
          if (![404, 410].includes(e.status)) throw e;
        }
      }
      if (lifecycle.current.signal.aborted) return false;
      setJob(null);
      setReport(null);
      remember(null);
      return true;
    } catch (e) {
      if (e.name !== "AbortError") setError(e.message);
      return false;
    } finally {
      if (!lifecycle.current.signal.aborted) setBusy(null);
    }
  }
  async function download() {
    if (!job?.download_available || busy) return;
    setBusy("download");
    setError("");
    try {
      const response = await request(`/${job.id}/download`, {
        signal: lifecycle.current.signal,
      });
      const blob = await response.blob();
      if (lifecycle.current.signal.aborted) return;
      const url = URL.createObjectURL(blob),
        anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = downloadName(
        response.headers.get("Content-Disposition"),
        job.original_filename.replace(/\.(docx|pdf)$/i, ".zip"),
      );
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      if (e.name !== "AbortError") setError(e.message);
    } finally {
      if (!lifecycle.current.signal.aborted) setBusy(null);
    }
  }
  return {
    session,
    job,
    report,
    error,
    progress,
    busy,
    convert,
    reset,
    download,
    cancelUpload: () => pendingUpload.current?.abort(),
    clearError: () => setError(""),
    reconnect: () => setConnection((v) => v + 1),
  };
}
