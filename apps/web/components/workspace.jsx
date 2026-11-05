"use client";
import { useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  Check,
  CheckCheck,
  ChevronRight,
  CircleHelp,
  CloudUpload,
  FileCheck2,
  FileText,
  Files,
  FolderOpen,
  Layers3,
  LoaderCircle,
  LockKeyhole,
  LogOut,
  Moon,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sun,
  Trash2,
  TriangleAlert,
  X,
} from "lucide-react";
import useWorkspace from "../hooks/use-workspace";
import { json } from "../lib/api.mjs";
import {
  bytes,
  resumable,
  stageIndex,
  stages,
  terminal,
  validateSelection,
} from "../lib/jobs.mjs";
import Preview from "./preview";

function Badge({ job }) {
  const labels = {
    queued: "Queued",
    running: "Processing",
    completed: "Validated",
    failed: "Needs attention",
    blocked: "Blocked",
    expired: "Expired",
    cancelled: "Cancelled",
  };
  return (
    <span className={`state-badge state-${job.state}`}>
      {job.state === "running" ? (
        <LoaderCircle size={12} className="spin" />
      ) : (
        <span className="status-dot" />
      )}
      {labels[job.state] || job.state}
    </span>
  );
}

function JobDetail({ job, token, action, download }) {
  const [tab, setTab] = useState("checks"),
    [report, setReport] = useState(null),
    [error, setError] = useState(""),
    [pending, setPending] = useState(false),
    [confirm, setConfirm] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setReport(null);
    setError("");
    setConfirm(false);
    json(`/${job.id}/validation`, token, { signal: controller.signal })
      .then(setReport)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, [job.id, job.version, token]);
  const processing = report?.document_processing;
  const index = stageIndex(job);
  const run = async (fn) => {
    setPending(true);
    try {
      await fn();
    } finally {
      setPending(false);
    }
  };
  const checks = [
    [
      "Accepted revisions",
      processing?.revision_acceptance?.after?.total === 0 &&
        processing?.revision_acceptance?.source_unchanged,
      processing?.revision_acceptance,
    ],
    [
      "PDF reference fidelity",
      processing?.pdf_validation?.passed,
      processing?.pdf_validation,
    ],
    [
      "Local SEC validation",
      processing?.sec_validation?.strict_passed,
      processing?.sec_validation,
    ],
    [
      "Visual comparison",
      processing?.visual_validation?.strict_passed,
      processing?.visual_validation,
    ],
    ["Final package", report?.complete, processing?.packaging],
  ];
  const diagnostics = [
    ...(report?.diagnostics || []),
    ...(processing?.sec_validation?.diagnostics || []),
    ...(processing?.visual_validation?.diagnostics || []),
    ...(processing?.pdf_validation?.diagnostics || []),
  ];
  return (
    <section className="detail-panel" aria-label="Selected document">
      <div className="detail-heading">
        <div className="document-icon">
          <FileText size={22} />
        </div>
        <div className="min-zero">
          <h3 title={job.original_filename}>{job.original_filename}</h3>
          <p>Conversion details</p>
        </div>
        <Badge job={job} />
      </div>
      <div
        className="tabs tabs-border detail-tabs"
        role="tablist"
        aria-label="Document details"
        onKeyDown={(event) => {
          if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key))
            return;
          event.preventDefault();
          const next =
            event.key === "Home"
              ? "checks"
              : event.key === "End"
                ? "preview"
                : tab === "checks"
                  ? "preview"
                  : "checks";
          setTab(next);
          document.getElementById(`${next}-tab`).focus();
        }}
      >
        <button
          role="tab"
          aria-selected={tab === "checks"}
          tabIndex={tab === "checks" ? 0 : -1}
          aria-controls="checks-panel"
          id="checks-tab"
          className={`tab ${tab === "checks" ? "tab-active" : ""}`}
          onClick={() => setTab("checks")}
        >
          Status & checks
        </button>
        <button
          role="tab"
          aria-selected={tab === "preview"}
          tabIndex={tab === "preview" ? 0 : -1}
          aria-controls="preview-panel"
          id="preview-tab"
          className={`tab ${tab === "preview" ? "tab-active" : ""}`}
          onClick={() => setTab("preview")}
        >
          Preview & compare
        </button>
      </div>
      <div
        hidden={tab !== "checks"}
        role="tabpanel"
        id="checks-panel"
        aria-labelledby="checks-tab"
        className="checks-content"
      >
        <div className="stage-track" aria-label="Processing stages">
          {stages.map(([key, label], n) => {
            const complete =
              (index >= 0 && n < index) || job.state === "completed";
            const current = n === index && !terminal.has(job.state);
            return (
              <div
                key={key}
                className={`track-item ${complete ? "done" : ""} ${current ? "current" : ""}`}
                aria-current={current ? "step" : undefined}
              >
                <span>{complete ? <Check size={12} /> : n + 1}</span>
                <p>{label}</p>
              </div>
            );
          })}
        </div>
        <div className="check-summary">
          {checks.map(([label, passed, exists]) => (
            <div key={label}>
              <span>{label}</span>
              <strong
                className={
                  passed
                    ? "check-pass"
                    : exists
                      ? "check-fail"
                      : "check-pending"
                }
              >
                {passed ? "Passed" : exists ? "Not passed" : "Pending"}
              </strong>
            </div>
          ))}
        </div>
        {error && (
          <p role="alert" className="inline-error">
            {error}
          </p>
        )}
        {(diagnostics.length > 0 || job.diagnostic_code) && (
          <div className="diagnostics">
            <h4>
              <TriangleAlert size={16} /> Review required
            </h4>
            {diagnostics.length ? (
              diagnostics.slice(0, 50).map((item, n) => (
                <article key={n}>
                  <code>{item.code}</code>
                  <p>
                    {item.description ||
                      item.message ||
                      "Review the diagnostic details."}
                  </p>
                  {(item.section || item.manual_section) && (
                    <small>Manual: {item.section || item.manual_section}</small>
                  )}
                  {item.remediation && <small>{item.remediation}</small>}
                </article>
              ))
            ) : (
              <code>{job.diagnostic_code}</code>
            )}
            {diagnostics.length > 50 && (
              <p>Showing 50 of {diagnostics.length} diagnostics.</p>
            )}
          </div>
        )}
        <details className="job-reference">
          <summary>Job reference</summary>
          <code>{job.id}</code>
          <p>
            Retained until {new Date(job.expires_at).toLocaleString()}. Keep the
            ID to reopen this job.
          </p>
        </details>
      </div>
      <div
        hidden={tab !== "preview"}
        role="tabpanel"
        id="preview-panel"
        aria-labelledby="preview-tab"
      >
        {tab === "preview" && <Preview job={job} token={token} />}
      </div>
      <div className="detail-actions">
        <p>
          <LockKeyhole size={13} /> Downloads require all checks to pass.
        </p>
        <div>
          {confirm ? (
            <>
              <span>Remove this job and its files?</span>
              <button
                className="btn btn-sm btn-error"
                disabled={pending}
                onClick={() => run(() => action(job, "delete"))}
              >
                Remove job
              </button>
              <button
                className="btn btn-sm btn-ghost"
                onClick={() => setConfirm(false)}
              >
                Keep
              </button>
            </>
          ) : (
            <button
              className="btn btn-sm btn-ghost"
              aria-label="Remove selected job"
              onClick={() => setConfirm(true)}
            >
              <Trash2 size={15} />
              {job.state === "running" || job.state === "queued"
                ? "Cancel"
                : "Remove"}
            </button>
          )}
          {job.state === "blocked" && resumable.has(job.diagnostic_code) && (
            <button
              className="btn btn-sm"
              disabled={pending}
              onClick={() => run(() => action(job, "resume"))}
            >
              <RefreshCw size={14} />
              Retry processing
            </button>
          )}
          <button
            className="btn btn-sm btn-primary"
            disabled={!job.download_available || pending}
            onClick={() => run(() => download(job))}
          >
            <ArrowDownToLine size={15} />
            {pending ? "Working…" : "Download ZIP"}
          </button>
        </div>
      </div>
    </section>
  );
}

export default function Workspace() {
  const ws = useWorkspace();
  const [credential, setCredential] = useState(""),
    [files, setFiles] = useState([]),
    [selectionErrors, setSelectionErrors] = useState([]);
  const [selected, setSelected] = useState(""),
    [filter, setFilter] = useState("all"),
    [search, setSearch] = useState(""),
    [drag, setDrag] = useState(false);
  const [dark, setDark] = useState(false),
    [help, setHelp] = useState(false),
    [recoveryId, setRecoveryId] = useState("");
  const input = useRef(null),
    helpDialog = useRef(null);
  useEffect(() => {
    const dialog = helpDialog.current;
    if (!help || !dialog) return;
    dialog.showModal();
    return () => dialog.close();
  }, [help]);
  useEffect(() => {
    const preference = localStorage.getItem("convx-theme");
    setDark(
      preference
        ? preference === "dark"
        : window.matchMedia("(prefers-color-scheme: dark)").matches,
    );
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("convx-theme", dark ? "dark" : "light");
  }, [dark]);
  const limits = ws.session || {
    max_upload_bytes: 20971520,
    max_batch_files: 10,
    max_request_bytes: 104857600,
  };
  const choose = (incoming) => {
    const result = validateSelection(
      [...files, ...Array.from(incoming)],
      limits,
    );
    const unique = result.valid.filter(
      (file, n, all) =>
        all.findIndex(
          (other) =>
            other.name === file.name &&
            other.size === file.size &&
            other.lastModified === file.lastModified,
        ) === n,
    );
    if (
      unique.reduce((sum, file) => sum + file.size, 0) + unique.length * 1024 >
      limits.max_request_bytes
    ) {
      setSelectionErrors([
        "This batch exceeds the request limit. Upload fewer documents at a time.",
      ]);
      return;
    }
    setFiles(unique);
    setSelectionErrors(result.errors);
  };
  const connect = async (token) => {
    setFiles([]);
    setSelected("");
    setSelectionErrors([]);
    await ws.connect(token);
    setCredential("");
  };
  const current = ws.jobs.find((job) => job.id === selected) || ws.jobs[0];
  const counts = {
    all: ws.jobs.length,
    processing: ws.jobs.filter((job) => !terminal.has(job.state)).length,
    attention: ws.jobs.filter((job) =>
      ["failed", "blocked"].includes(job.state),
    ).length,
    ready: ws.jobs.filter((job) => job.download_available).length,
  };
  const visible = ws.jobs.filter(
    (job) =>
      job.original_filename.toLowerCase().includes(search.toLowerCase()) &&
      (filter === "all" ||
        (filter === "processing" && !terminal.has(job.state)) ||
        (filter === "attention" && ["failed", "blocked"].includes(job.state)) ||
        (filter === "ready" && job.download_available)),
  );
  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        Skip to workspace
      </a>
      <aside className="sidebar">
        <a href="/" className="brand" aria-label="ConvX home">
          <span className="brand-mark">
            <Layers3 size={23} />
          </span>
          ConvX<span className="brand-dot">.</span>
        </a>
        <div className="sidebar-caption">DOCUMENT WORKSPACE</div>
        <nav aria-label="Main navigation">
          <a href="#main" className="nav-active">
            <FolderOpen size={18} />
            Conversions<span>{ws.jobs.length}</span>
          </a>
          <button onClick={() => setHelp(true)}>
            <CircleHelp size={18} />
            How it works
          </button>
        </nav>
        <div className="sidebar-bottom">
          <div className="shield-icon">
            <ShieldCheck size={21} />
          </div>
          <strong>Fidelity comes first.</strong>
          <p>
            Each filing is checked for content, compliance and visual accuracy.
          </p>
          <div className="sidebar-divider" />
          <span className="edition">CONVX / FILING TOOLS</span>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace
            <ChevronRight size={14} />
            <span>Conversions</span>
          </div>
          <div className="header-actions">
            <span className={`connection ${ws.session ? "connected" : ""}`}>
              <span />
              {ws.session ? "Connected" : "Not connected"}
            </span>
            <button
              className="btn btn-ghost btn-sm btn-square"
              aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
              onClick={() => setDark((value) => !value)}
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            {ws.session && (
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => {
                  ws.disconnect();
                  setFiles([]);
                  setSelected("");
                }}
              >
                <LogOut size={15} />
                Disconnect
              </button>
            )}
          </div>
        </header>
        <main id="main">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                <span />
                THE FILING WORKSPACE
              </div>
              <h1>Every detail matters.</h1>
              <p>
                Convert your Word documents. Review every check. File with
                clarity.
              </p>
            </div>
            <div className="workflow-pill">
              <FileText size={15} />
              <span>DOCX</span>
              <ArrowRight size={13} />
              <span>PDF</span>
              <ArrowRight size={13} />
              <span>HTM + assets</span>
            </div>
          </div>
          {!ws.session && (
            <section
              className="connection-card"
              aria-labelledby="connect-title"
            >
              <div>
                <LockKeyhole size={20} />
                <h2 id="connect-title">Connect to your workspace</h2>
                <p>
                  Use your API access token or local access on this computer.
                </p>
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  connect(credential);
                }}
              >
                <label className="sr-only" htmlFor="access-token">
                  API access token
                </label>
                <input
                  id="access-token"
                  type="password"
                  className="input"
                  placeholder="API access token"
                  value={credential}
                  onChange={(e) => setCredential(e.target.value)}
                  autoComplete="off"
                  spellCheck="false"
                />
                <button
                  className="btn btn-primary"
                  disabled={!credential || ws.connecting}
                >
                  {ws.connecting ? "Connecting…" : "Connect"}
                </button>
                <button
                  type="button"
                  className="btn btn-ghost"
                  disabled={ws.connecting}
                  onClick={() => connect("")}
                >
                  Use local access
                </button>
              </form>
            </section>
          )}
          {ws.error && (
            <div className="alert error-alert" role="alert">
              <TriangleAlert size={19} />
              <span>{ws.error}</span>
              <button
                className="btn btn-ghost btn-xs btn-square"
                aria-label="Dismiss error"
                onClick={ws.clearError}
              >
                <X size={16} />
              </button>
            </div>
          )}
          <section className="upload-card" aria-labelledby="upload-title">
            <div className="section-heading">
              <div>
                <h2 id="upload-title">Start a conversion</h2>
                <p>
                  One document or a whole batch. Every file gets its own checks.
                </p>
              </div>
              <span className="subtle-badge">.DOCX ONLY</span>
            </div>
            <div
              className={`drop-zone ${drag ? "dragging" : ""}`}
              onDragOver={(e) => {
                e.preventDefault();
                if (ws.session && !ws.busy) setDrag(true);
              }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDrag(false);
                if (ws.session && !ws.busy) choose(e.dataTransfer.files);
              }}
            >
              <span className="upload-icon">
                <CloudUpload size={28} strokeWidth={1.5} />
              </span>
              <h3>Drop your documents here</h3>
              <p>or choose files from your computer</p>
              <input
                ref={input}
                type="file"
                multiple
                accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                className="sr-only"
                aria-label="Choose DOCX files"
                disabled={!ws.session || ws.busy}
                onChange={(e) => {
                  choose(e.target.files);
                  e.target.value = "";
                }}
              />
              <button
                className="btn choose-button"
                disabled={!ws.session || ws.busy}
                onClick={() => input.current?.click()}
              >
                <Plus size={16} />
                Choose documents
              </button>
              <span className="upload-hint">
                Up to {bytes(limits.max_upload_bytes)} per file ·{" "}
                {limits.max_batch_files} documents per batch
              </span>
            </div>
            {selectionErrors.length > 0 && (
              <div className="selection-errors" role="alert">
                {selectionErrors.map((message, i) => (
                  <p key={i}>{message}</p>
                ))}
              </div>
            )}
            {files.length > 0 && (
              <div
                className="selected-files"
                aria-label="Selected upload files"
              >
                {files.map((file, n) => (
                  <div key={`${file.name}-${n}`}>
                    <FileText size={17} />
                    <span title={file.name}>{file.name}</span>
                    <small>{bytes(file.size)}</small>
                    <button
                      className="btn btn-ghost btn-xs btn-square"
                      aria-label={`Remove ${file.name}`}
                      disabled={ws.busy}
                      onClick={() =>
                        setFiles((previous) =>
                          previous.filter((_, i) => i !== n),
                        )
                      }
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
                <div className="upload-submit">
                  <span aria-live="polite">
                    {ws.progress !== null
                      ? `Uploading ${ws.progress}%${ws.progress === 100 ? " · validating upload…" : ""}`
                      : `${files.length} document${files.length === 1 ? "" : "s"} selected`}
                  </span>
                  <button
                    className="btn btn-primary"
                    disabled={ws.busy || !ws.session}
                    onClick={async () => {
                      if (await ws.uploadFiles(files)) setFiles([]);
                    }}
                  >
                    {ws.busy ? (
                      <LoaderCircle size={16} className="spin" />
                    ) : (
                      <ArrowRight size={16} />
                    )}
                    {ws.busy ? "Uploading…" : "Start conversion"}
                  </button>
                </div>
                {ws.progress !== null && (
                  <progress
                    className="progress progress-primary"
                    value={ws.progress}
                    max="100"
                    aria-label="Upload progress"
                  />
                )}
              </div>
            )}
            <div className="upload-footer">
              <LockKeyhole size={13} />
              <span>
                Private processing · Original documents stay unchanged
              </span>
              <span className="footer-note">
                PDF-first. Searchable HTM. Clean ZIP.
              </span>
            </div>
          </section>
          <section
            className="documents-section"
            aria-labelledby="documents-title"
          >
            <div className="section-heading">
              <div>
                <h2 id="documents-title">
                  Your conversions{" "}
                  <span className="count-chip">{ws.jobs.length}</span>
                </h2>
                <p>Follow progress and review your documents in one place.</p>
              </div>
              <label className="search-field">
                <Search size={16} />
                <span className="sr-only">Search documents</span>
                <input
                  placeholder="Search documents"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </label>
            </div>
            <div className="filter-bar" aria-label="Filter conversions">
              {[
                ["all", "All documents"],
                ["processing", "Processing"],
                ["attention", "Needs attention"],
                ["ready", "Ready to download"],
              ].map(([key, label]) => (
                <button
                  key={key}
                  aria-pressed={filter === key}
                  className={filter === key ? "active" : ""}
                  onClick={() => setFilter(key)}
                >
                  {label}
                  <span>{counts[key]}</span>
                </button>
              ))}
            </div>
            {visible.length ? (
              <div className="job-table-wrap">
                <table className="job-table">
                  <thead>
                    <tr>
                      <th>Document</th>
                      <th>Status</th>
                      <th>Current stage</th>
                      <th>
                        <span className="sr-only">Open details</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {visible.map((job) => (
                      <tr
                        key={job.id}
                        className={current?.id === job.id ? "selected-row" : ""}
                      >
                        <td>
                          <button
                            className="document-button"
                            onClick={() => setSelected(job.id)}
                          >
                            <span className="small-doc-icon">
                              <FileText size={18} />
                            </span>
                            <span>
                              <strong>{job.original_filename}</strong>
                              <small>
                                {new Date(job.created_at).toLocaleString()}
                              </small>
                            </span>
                          </button>
                        </td>
                        <td>
                          <Badge job={job} />
                        </td>
                        <td className="stage-label">
                          {stages[stageIndex(job)]?.[1] ||
                            job.stage.replaceAll("_", " ")}
                        </td>
                        <td>
                          <button
                            className="btn btn-ghost btn-sm btn-square"
                            aria-label={`Review ${job.original_filename}`}
                            onClick={() => setSelected(job.id)}
                          >
                            <ChevronRight size={17} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-art">
                  <Files size={30} strokeWidth={1.3} />
                  <span>
                    <CheckCheck size={13} />
                  </span>
                </div>
                <h3>
                  {ws.jobs.length
                    ? "No matching documents"
                    : "A clear path from document to filing"}
                </h3>
                <p>
                  {ws.jobs.length
                    ? "Try another search or filter."
                    : "Your conversions will appear here, with progress and validation for every document."}
                </p>
                {!ws.jobs.length && (
                  <div className="empty-steps">
                    <span>
                      <FileText size={14} />
                      Upload DOCX
                    </span>
                    <ChevronRight size={12} />
                    <span>
                      <ShieldCheck size={14} />
                      Review checks
                    </span>
                    <ChevronRight size={12} />
                    <span>
                      <FileCheck2 size={14} />
                      Download ZIP
                    </span>
                  </div>
                )}
              </div>
            )}
            {current && (
              <JobDetail
                key={current.id}
                job={current}
                token={ws.token}
                action={ws.action}
                download={ws.download}
              />
            )}
          </section>
          {ws.session && (
            <details className="recover-job">
              <summary>Reopen a previous job</summary>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  ws.recover(recoveryId.trim());
                }}
              >
                <label htmlFor="recover-id">Job ID</label>
                <input
                  id="recover-id"
                  className="input input-sm"
                  value={recoveryId}
                  onChange={(e) => setRecoveryId(e.target.value)}
                  placeholder="Paste your job ID"
                />
                <button className="btn btn-sm" type="submit">
                  Open job
                </button>
              </form>
            </details>
          )}
          <footer className="page-footer">
            <span>
              ConvX{" "}
              <span className="muted">/ Document conversion with care</span>
            </span>
            <button onClick={() => setHelp(true)}>
              How validation works
              <ArrowRight size={13} />
            </button>
          </footer>
        </main>
      </div>
      {help && (
        <dialog
          ref={helpDialog}
          className="modal"
          aria-labelledby="help-title"
          onCancel={() => setHelp(false)}
        >
          <div className="modal-box">
            <button
              className="btn btn-ghost btn-sm btn-square modal-close"
              aria-label="Close help"
              autoFocus
              onClick={() => setHelp(false)}
            >
              <X size={18} />
            </button>
            <h2 id="help-title">A check at every step.</h2>
            <p>
              ConvX accepts supported tracked revisions, exports an accepted
              DOCX to PDF, reconstructs searchable HTM, and checks its content,
              SEC markup and visual appearance.
            </p>
            <p>
              A ZIP becomes downloadable only after every required check passes.
              Failed or blocked documents show diagnostics. Preview images are
              for review and do not establish SEC acceptance.
            </p>
            <p>
              Access tokens stay in this page’s memory. Only job IDs and your
              theme preference are saved in this browser. Disconnect to clear
              the tab’s job list.
            </p>
            <p>
              The current Word-reference conversion still fails strict fidelity.
              No premium renderer or paid service is used.
            </p>
            <button className="btn btn-primary" onClick={() => setHelp(false)}>
              Back to workspace
            </button>
          </div>
          <button
            className="modal-backdrop"
            aria-label="Close help dialog"
            onClick={() => setHelp(false)}
          />
        </dialog>
      )}
    </div>
  );
}
