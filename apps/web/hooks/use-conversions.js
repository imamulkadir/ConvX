"use client";
import { useEffect, useRef, useState } from "react";
import { json, request, upload } from "../lib/api.mjs";
import { downloadName, terminal } from "../lib/jobs.mjs";

export default function useConversions() {
  const [session, setSession] = useState(null),
    [jobs, setJobs] = useState([]);
  const [error, setError] = useState(""),
    [progress, setProgress] = useState(null),
    [busy, setBusy] = useState(false);
  const controller = useRef(null),
    jobsRef = useRef(jobs);
  jobsRef.current = jobs;
  useEffect(() => {
    const lifecycle = new AbortController();
    controller.current = lifecycle;
    (async () => {
      const limits = await json("/session", { signal: lifecycle.signal });
      let ids = [];
      try {
        ids = JSON.parse(sessionStorage.getItem("convx-jobs") || "[]");
      } catch {
        /* Corrupt tab state grants no access. */
      }
      if (!Array.isArray(ids)) ids = [];
      const restored = await Promise.allSettled(
        ids
          .slice(0, 100)
          .filter((id) => typeof id === "string" && /^[a-f0-9-]{36}$/.test(id))
          .map((id) => json(`/${id}`, { signal: lifecycle.signal })),
      );
      if (!lifecycle.signal.aborted) {
        setJobs(
          restored
            .filter((item) => item.status === "fulfilled")
            .map((item) => item.value),
        );
        setSession(limits);
      }
    })().catch((e) => {
      if (!lifecycle.signal.aborted) setError(e.message);
    });
    return () => lifecycle.abort();
  }, []);
  useEffect(() => {
    if (session)
      sessionStorage.setItem(
        "convx-jobs",
        JSON.stringify(jobs.map((job) => job.id)),
      );
  }, [jobs, session]);
  useEffect(() => {
    if (!session) return;
    let cancelled = false,
      timer;
    async function poll() {
      const current = jobsRef.current.filter((job) => !terminal.has(job.state));
      const results = await Promise.allSettled(
        current.map((job) =>
          json(`/${job.id}`, { signal: controller.current.signal }),
        ),
      );
      if (cancelled) return;
      const updates = results
        .filter((item) => item.status === "fulfilled")
        .map((item) => item.value);
      if (updates.length)
        setJobs((previous) =>
          previous.map(
            (job) => updates.find((item) => item.id === job.id) || job,
          ),
        );
      const failed = results.some((item) => item.status === "rejected");
      if (failed)
        setError("Connection lost. Status updates will retry automatically.");
      timer = setTimeout(poll, failed ? 5000 : 1500);
    }
    timer = setTimeout(poll, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [session]);
  async function uploadFiles(files) {
    const signal = controller.current.signal;
    setBusy(true);
    setProgress(0);
    setError("");
    try {
      const result = await upload(
        files,
        (value) => {
          if (!signal.aborted) setProgress(value);
        },
        signal,
      );
      if (signal.aborted) return false;
      setJobs((previous) => [...result.jobs, ...previous].slice(0, 100));
      if (result.errors.length)
        setError(
          result.errors
            .map((item) => `${item.filename}: ${item.message}`)
            .join("\n"),
        );
      return result.errors.length === 0;
    } catch (e) {
      if (!signal.aborted) setError(e.message);
      return false;
    } finally {
      if (!signal.aborted) {
        setBusy(false);
        setProgress(null);
      }
    }
  }
  async function action(job, type) {
    const signal = controller.current.signal;
    setError("");
    try {
      await json(`/${job.id}${type === "resume" ? "/resume" : ""}`, {
        method: type === "resume" ? "POST" : "DELETE",
        signal,
      });
      if (signal.aborted) return;
      if (type === "resume") {
        const fresh = await json(`/${job.id}`, { signal });
        if (!signal.aborted)
          setJobs((previous) =>
            previous.map((item) => (item.id === job.id ? fresh : item)),
          );
      } else
        setJobs((previous) => previous.filter((item) => item.id !== job.id));
    } catch (e) {
      if (!signal.aborted) setError(e.message);
    }
  }
  async function download(job) {
    const signal = controller.current.signal;
    setError("");
    try {
      const response = await request(`/${job.id}/download`, { signal }),
        blob = await response.blob();
      if (signal.aborted) return;
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
      if (!signal.aborted) setError(e.message);
    }
  }
  async function recover(id) {
    if (!/^[a-f0-9-]{36}$/.test(id)) {
      setError("Enter a valid document reference.");
      return;
    }
    const signal = controller.current.signal;
    try {
      const job = await json(`/${id}`, { signal });
      if (!signal.aborted)
        setJobs((previous) =>
          [job, ...previous.filter((item) => item.id !== id)].slice(0, 100),
        );
    } catch (e) {
      if (!signal.aborted) setError(e.message);
    }
  }
  return {
    session,
    jobs,
    error,
    progress,
    busy,
    uploadFiles,
    action,
    download,
    recover,
    clearError: () => setError(""),
  };
}
