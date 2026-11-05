"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { json, request, upload } from "../lib/api.mjs";
import { downloadName, terminal } from "../lib/jobs.mjs";

export default function useWorkspace() {
  const [session, setSession] = useState(null),
    [jobs, setJobs] = useState([]);
  const [error, setError] = useState(""),
    [progress, setProgress] = useState(null);
  const [busy, setBusy] = useState(false),
    [connecting, setConnecting] = useState(false);
  const epoch = useRef(0),
    controller = useRef(null),
    token = useRef("");
  const jobsRef = useRef(jobs);
  jobsRef.current = jobs;
  const disconnect = useCallback(() => {
    epoch.current++;
    controller.current?.abort();
    token.current = "";
    setSession(null);
    setJobs([]);
    setProgress(null);
    setBusy(false);
    setConnecting(false);
    setError("");
    sessionStorage.removeItem("convx-jobs");
  }, []);
  const connect = useCallback(async (credential) => {
    const current = ++epoch.current;
    controller.current?.abort();
    controller.current = new AbortController();
    setConnecting(true);
    setError("");
    setJobs([]);
    setSession(null);
    token.current = "";
    try {
      const limits = await json("/session", credential, {
        signal: controller.current.signal,
      });
      if (epoch.current !== current) return;
      token.current = credential;
      setSession(limits);
      let ids = [];
      try {
        ids = JSON.parse(sessionStorage.getItem("convx-jobs") || "[]");
      } catch {
        /* Ignore damaged tab state. */
      }
      if (!Array.isArray(ids)) ids = [];
      const result = await Promise.allSettled(
        ids
          .slice(0, 100)
          .filter((id) => typeof id === "string" && /^[a-f0-9-]{36}$/.test(id))
          .map((id) =>
            json(`/${id}`, credential, { signal: controller.current.signal }),
          ),
      );
      if (epoch.current === current)
        setJobs(
          result.filter((r) => r.status === "fulfilled").map((r) => r.value),
        );
    } catch (e) {
      if (epoch.current === current && e.name !== "AbortError")
        setError(e.message);
    } finally {
      if (epoch.current === current) setConnecting(false);
    }
  }, []);
  useEffect(
    () => () => {
      epoch.current++;
      controller.current?.abort();
    },
    [],
  );
  useEffect(() => {
    if (!session) return;
    sessionStorage.setItem(
      "convx-jobs",
      JSON.stringify(jobs.map((job) => job.id)),
    );
  }, [jobs, session]);
  useEffect(() => {
    if (!session) return;
    let cancelled = false,
      timer;
    const current = epoch.current;
    async function poll() {
      const active = jobsRef.current.filter((job) => !terminal.has(job.state));
      const results = await Promise.allSettled(
        active.map((job) =>
          json(`/${job.id}`, token.current, {
            signal: controller.current.signal,
          }),
        ),
      );
      if (cancelled || epoch.current !== current) return;
      const updates = results
        .filter((r) => r.status === "fulfilled")
        .map((r) => r.value);
      if (updates.length)
        setJobs((previous) =>
          previous.map(
            (job) => updates.find((update) => update.id === job.id) || job,
          ),
        );
      const failures = results.filter(
        (r) => r.status === "rejected" && r.reason.name !== "AbortError",
      );
      if (failures.length)
        setError(
          "Status refresh failed. Check your connection or reconnect; uploaded jobs continue independently.",
        );
      timer = setTimeout(poll, failures.length ? 5000 : 1500);
    }
    timer = setTimeout(poll, 500);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [session]);
  const uploadFiles = async (files) => {
    const current = epoch.current;
    setBusy(true);
    setError("");
    setProgress(0);
    try {
      const result = await upload(
        files,
        token.current,
        (value) => {
          if (epoch.current === current) setProgress(value);
        },
        controller.current.signal,
      );
      if (epoch.current !== current) return false;
      setJobs((previous) => [...result.jobs, ...previous].slice(0, 100));
      if (result.errors.length)
        setError(
          result.errors
            .map((item) => `${item.filename}: ${item.message}`)
            .join("\n"),
        );
      return true;
    } catch (e) {
      if (epoch.current === current && e.name !== "AbortError")
        setError(e.message);
      return false;
    } finally {
      if (epoch.current === current) {
        setBusy(false);
        setProgress(null);
      }
    }
  };
  const action = async (job, type) => {
    const current = epoch.current;
    setError("");
    try {
      await json(
        `/${job.id}${type === "resume" ? "/resume" : ""}`,
        token.current,
        {
          method: type === "resume" ? "POST" : "DELETE",
          signal: controller.current.signal,
        },
      );
      if (epoch.current !== current) return;
      if (type === "resume") {
        const fresh = await json(`/${job.id}`, token.current, {
          signal: controller.current.signal,
        });
        if (epoch.current === current)
          setJobs((previous) =>
            previous.map((item) => (item.id === job.id ? fresh : item)),
          );
      } else
        setJobs((previous) => previous.filter((item) => item.id !== job.id));
    } catch (e) {
      if (epoch.current === current && e.name !== "AbortError")
        setError(e.message);
    }
  };
  const download = async (job) => {
    const current = epoch.current;
    setError("");
    try {
      const response = await request(`/${job.id}/download`, token.current, {
        signal: controller.current.signal,
      });
      const blob = await response.blob();
      if (epoch.current !== current) return;
      const url = URL.createObjectURL(blob),
        anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = downloadName(
        response.headers.get("Content-Disposition"),
        job.original_filename.replace(/\.docx$/i, ".zip"),
      );
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      if (epoch.current === current && e.name !== "AbortError")
        setError(e.message);
    }
  };
  const recover = async (id) => {
    if (!/^[a-f0-9-]{36}$/.test(id)) {
      setError("Enter a valid job ID.");
      return;
    }
    const current = epoch.current;
    try {
      const job = await json(`/${id}`, token.current, {
        signal: controller.current.signal,
      });
      if (epoch.current === current)
        setJobs((previous) =>
          [job, ...previous.filter((item) => item.id !== id)].slice(0, 100),
        );
    } catch (e) {
      if (epoch.current === current && e.name !== "AbortError")
        setError(e.message);
    }
  };
  return {
    session,
    jobs,
    error,
    progress,
    busy,
    connecting,
    connect,
    disconnect,
    uploadFiles,
    action,
    download,
    recover,
    token: token.current,
    clearError: () => setError(""),
  };
}
