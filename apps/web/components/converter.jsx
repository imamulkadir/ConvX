"use client";

import { useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  Check,
  FileText,
  FileUp,
  LoaderCircle,
  Moon,
  Sun,
  X,
} from "lucide-react";
import useConversion from "../hooks/use-conversions";
import {
  bytes,
  failureMessage,
  progressMessage,
  terminal,
  validateSelection,
  warningMessage,
} from "../lib/jobs.mjs";
import Preview from "./preview";

export default function Converter() {
  const flow = useConversion();
  const [file, setFile] = useState(null);
  const [edgar, setEdgar] = useState(false);
  const [selectionError, setSelectionError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [dark, setDark] = useState(false);
  const [preview, setPreview] = useState(false);
  const input = useRef(null),
    chooseButton = useRef(null);
  const job = flow.job;
  const processing = job && !terminal.has(job.state);
  const locked = Boolean(job || flow.busy);
  const limits = flow.session || {
    max_upload_bytes: 20971520,
    max_batch_files: 1,
  };
  const report = flow.report?.document_processing;
  const diagnostics = report?.diagnostics || flow.report?.diagnostics || [];
  const errors = diagnostics.filter((d) => d.severity !== "warning");
  const warnings = [
    ...new Map(
      diagnostics
        .filter(
          (d) => d.severity === "warning" && d.code !== "EDGAR_LOCAL_PROFILE",
        )
        .map((d) => [d.code, d]),
    ).values(),
  ];
  const ready = job?.state === "completed" && job.download_available;
  const failed = job && ["failed", "blocked", "expired"].includes(job.state);

  useEffect(() => {
    let preference;
    try {
      preference = localStorage.getItem("convx-theme");
    } catch {
      /* Optional preference storage. */
    }
    const next = preference
      ? preference === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    setDark(next);
    document.documentElement.dataset.theme = next ? "dark" : "light";
  }, []);
  useEffect(() => {
    if (job) setEdgar(job.mode === "edgar");
  }, [job?.id]);
  function theme() {
    const next = !dark;
    setDark(next);
    document.documentElement.dataset.theme = next ? "dark" : "light";
    try {
      localStorage.setItem("convx-theme", next ? "dark" : "light");
    } catch {
      /* Optional preference storage. */
    }
  }
  function select(incoming) {
    if (locked) return;
    const files = Array.from(incoming);
    const result = validateSelection(files, { ...limits, max_batch_files: 1 });
    setSelectionError(
      files.length > 1
        ? "Choose one document at a time."
        : result.errors.join(" "),
    );
    setFile(
      files.length === 1 && result.valid.length === 1 ? result.valid[0] : null,
    );
    flow.clearError();
  }
  function clear() {
    setFile(null);
    setSelectionError("");
    if (input.current) input.current.value = "";
    requestAnimationFrame(() => chooseButton.current?.focus());
  }
  async function reset() {
    if (await flow.reset()) {
      clear();
      setEdgar(false);
      setPreview(false);
    }
  }

  return (
    <div className="converter-shell">
      <a className="skip-link" href="#converter-form">
        Skip to converter
      </a>
      <header className="converter-header">
        <a className="converter-brand" href="/" aria-label="ConvX home">
          <span className="brand-icon">
            <FileText size={21} aria-hidden="true" />
          </span>
          ConvX<span className="brand-period">.</span>
        </a>
        <button
          type="button"
          className="btn btn-ghost btn-circle theme-button"
          aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
          onClick={theme}
        >
          {dark ? (
            <Sun size={19} aria-hidden="true" />
          ) : (
            <Moon size={19} aria-hidden="true" />
          )}
        </button>
      </header>
      <main className="converter-main">
        <div className="converter-heading">
          <p className="eyebrow">DOCUMENT CONVERSION, SIMPLIFIED</p>
          <h1>DOCX &amp; PDF to HTM Converter</h1>
          <p className="subtitle">
            Convert Word and PDF documents into high-fidelity HTM with optional
            SEC EDGAR compliance.
          </p>
        </div>
        <section className="converter-card" aria-label="Document converter">
          <form
            id="converter-form"
            onSubmit={(event) => {
              event.preventDefault();
              if (file && !locked && flow.session)
                flow.convert(file, edgar ? "edgar" : "standard");
            }}
          >
            <div className="form-section">
              <div className="section-caption">
                <span className="step-number">1</span>
                <h2>Choose your document</h2>
              </div>
              <div
                className={`upload-zone ${dragging ? "is-dragging" : ""}`}
                onDragOver={(event) => {
                  event.preventDefault();
                  if (!locked) setDragging(true);
                }}
                onDragLeave={(event) => {
                  if (!event.currentTarget.contains(event.relatedTarget))
                    setDragging(false);
                }}
                onDrop={(event) => {
                  event.preventDefault();
                  setDragging(false);
                  select(event.dataTransfer.files);
                }}
              >
                <div className="upload-icon">
                  <FileUp size={27} strokeWidth={1.5} aria-hidden="true" />
                </div>
                <p className="upload-title">Drag and drop your document here</p>
                <p className="muted">or choose a file from your computer</p>
                <input
                  ref={input}
                  className="sr-only"
                  tabIndex={-1}
                  id="source-document"
                  type="file"
                  accept=".docx,.pdf"
                  aria-label="Choose DOCX or PDF document"
                  disabled={locked}
                  onChange={(event) => select(event.target.files)}
                />
                <button
                  ref={chooseButton}
                  className="btn choose-button"
                  type="button"
                  disabled={locked}
                  onClick={() => {
                    input.current.value = "";
                    input.current.click();
                  }}
                >
                  Choose file
                </button>
                <p className="file-hint">
                  DOCX or PDF <span aria-hidden="true">·</span> Up to{" "}
                  {bytes(limits.max_upload_bytes)}
                </p>
              </div>
              {(file || job) && (
                <div className="selected-document">
                  <FileText size={21} aria-hidden="true" />
                  <div>
                    <strong>{job?.original_filename || file?.name}</strong>
                    <span className="muted">
                      {bytes(job?.source_bytes || file?.size || 0)}
                    </span>
                  </div>
                  {!job && (
                    <button
                      type="button"
                      className="btn btn-ghost btn-circle btn-sm"
                      aria-label="Clear selection"
                      disabled={Boolean(flow.busy)}
                      onClick={clear}
                    >
                      <X size={17} aria-hidden="true" />
                    </button>
                  )}
                </div>
              )}
              {selectionError && (
                <p className="form-error" role="alert">
                  {selectionError}
                </p>
              )}
            </div>
            <div className="mode-section">
              <label className="mode-choice">
                <input
                  className="checkbox checkbox-sm"
                  type="checkbox"
                  checked={edgar}
                  disabled={locked}
                  onChange={(event) => setEdgar(event.target.checked)}
                  aria-describedby="mode-description"
                />
                <span>
                  <strong>SEC EDGAR Compliance</strong>
                  <span className="optional" aria-hidden="true">
                    Optional
                  </span>
                </span>
              </label>
              <p id="mode-description" className="mode-description">
                {edgar
                  ? "EDGAR Mode — Uses only SEC-permitted HTML tags, attributes, and supported assets."
                  : "Standard Mode — Modern HTML5 and CSS for maximum formatting fidelity."}
              </p>
            </div>
            <div className="convert-section">
              <button
                className="btn btn-primary convert-button"
                type="submit"
                disabled={!file || locked || !flow.session}
              >
                {flow.busy === "upload" ? (
                  <LoaderCircle
                    size={18}
                    className="spinner"
                    aria-hidden="true"
                  />
                ) : (
                  <ArrowRight size={18} aria-hidden="true" />
                )}
                Convert to HTM
              </button>
              <p className="muted local-note">
                Processed locally. Your original document stays unchanged.
              </p>
            </div>
          </form>
          {flow.error && (
            <div className="result-block error-block" role="alert">
              <p>{flow.error}</p>
              {!flow.session && (
                <button className="btn btn-sm" onClick={flow.reconnect}>
                  Try again
                </button>
              )}
            </div>
          )}
          {(flow.busy === "upload" || processing) && (
            <div className="result-block" role="status" aria-live="polite">
              <div className="result-heading">
                <LoaderCircle
                  className="spinner"
                  size={20}
                  aria-hidden="true"
                />
                <strong>
                  {flow.busy === "upload"
                    ? "Uploading document"
                    : progressMessage(job)}
                </strong>
              </div>
              {flow.busy === "upload" && flow.progress !== null && (
                <progress
                  className="progress progress-primary"
                  max="100"
                  value={flow.progress}
                  aria-label="Upload progress"
                />
              )}
              <p className="muted">
                You can leave this tab open while your document is converted.
              </p>
              <button
                className="btn btn-ghost btn-sm"
                type="button"
                onClick={flow.busy === "upload" ? flow.cancelUpload : reset}
                disabled={flow.busy === "reset"}
              >
                {flow.busy === "upload" ? "Cancel upload" : "Cancel conversion"}
              </button>
            </div>
          )}
          {ready && (
            <div className="result-block success-block" aria-live="polite">
              <div className="result-heading">
                <Check size={21} aria-hidden="true" />
                <h2>Your ZIP is ready</h2>
              </div>
              <p className="output-name">
                {report?.packaging?.download_filename ||
                  job.original_filename.replace(/\.(pdf|docx)$/i, ".zip")}
              </p>
              <button
                type="button"
                className="btn btn-primary download-button"
                disabled={Boolean(flow.busy)}
                onClick={flow.download}
              >
                <ArrowDownToLine size={18} aria-hidden="true" />
                {flow.busy === "download"
                  ? "Preparing download…"
                  : "Download ZIP"}
              </button>
              {edgar && (
                <p className="result-note">
                  Local EDGAR checks passed. SEC filing acceptance is not
                  confirmed.
                </p>
              )}
              {warnings.length > 0 && (
                <details className="conversion-notes">
                  <summary>Conversion notes ({warnings.length})</summary>
                  <ul>
                    {warnings.map((d) => (
                      <li key={d.code}>{warningMessage(d)}</li>
                    ))}
                  </ul>
                </details>
              )}
              <button
                className="btn btn-ghost another-button"
                type="button"
                disabled={Boolean(flow.busy)}
                onClick={reset}
              >
                Convert another document
              </button>
            </div>
          )}
          {failed && (
            <div className="result-block error-block" role="alert">
              <h2>
                {job.state === "expired"
                  ? "This conversion has expired"
                  : "This document could not be converted"}
              </h2>
              <p>
                {failureMessage(errors[0]) ||
                  (job.state === "expired"
                    ? "Upload the document again to create a new ZIP."
                    : flow.report
                      ? "Try another document or use Standard Mode for complex layouts."
                      : "Loading conversion details…")}
              </p>
              {edgar && (
                <p>
                  Some document layouts cannot be reproduced within EDGAR
                  restrictions. Try Standard Mode for this document.
                </p>
              )}
              <button
                type="button"
                className="btn btn-sm"
                disabled={Boolean(flow.busy)}
                onClick={reset}
              >
                Choose another document
              </button>
            </div>
          )}
        </section>
        {job && terminal.has(job.state) && report?.generated_pdf_artifact && (
          <details
            className="preview-details"
            onToggle={(event) => setPreview(event.currentTarget.open)}
          >
            <summary>Preview and compare</summary>
            {preview && <Preview job={job} />}
          </details>
        )}
        <footer className="converter-footer">
          <p>One document. One ZIP. All required assets included.</p>
          <span>Temporary conversion files are removed automatically.</span>
        </footer>
      </main>
    </div>
  );
}
