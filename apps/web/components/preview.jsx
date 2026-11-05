"use client";
import { useEffect, useRef, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  ScanLine,
  Columns2,
} from "lucide-react";
import { json, request } from "../lib/api.mjs";

function Capture({ job, token, kind, page, zoom, dpi }) {
  const [naturalWidth, setNaturalWidth] = useState(null);
  const [url, setUrl] = useState(""),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true,
      objectUrl;
    const controller = new AbortController();
    setUrl("");
    setError("");
    request(`/${job.id}/preview?kind=${kind}&page=${page}`, token, {
      signal: controller.signal,
    })
      .then((response) => response.blob())
      .then((blob) => {
        if (active) {
          objectUrl = URL.createObjectURL(blob);
          setUrl(objectUrl);
        }
      })
      .catch((e) => {
        if (active && e.name !== "AbortError") setError(e.message);
      });
    return () => {
      active = false;
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [job.id, token, kind, page]);
  if (error)
    return (
      <p className="preview-message" role="status">
        {error}
      </p>
    );
  return url ? (
    <img
      className="preview-sheet"
      style={{
        width: naturalWidth
          ? `${(((naturalWidth * 96) / dpi) * zoom) / 100}px`
          : "auto",
      }}
      onLoad={(event) => setNaturalWidth(event.target.naturalWidth)}
      src={url}
      alt={`${kind === "htm" ? "Rendered HTM" : kind} diagnostic, page ${page}`}
    />
  ) : (
    <p className="preview-message" role="status">
      Loading capture…
    </p>
  );
}

function PdfPage({ job, token, page, zoom, onError }) {
  const canvas = useRef(null),
    [document, setDocument] = useState(null);
  useEffect(() => {
    let active = true,
      task,
      loaded;
    const controller = new AbortController();
    setDocument(null);
    (async () => {
      const pdfjs = await import("pdfjs-dist/build/pdf.mjs");
      pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
      const data = new Uint8Array(
        await (
          await request(`/${job.id}/preview?kind=pdf`, token, {
            signal: controller.signal,
          })
        ).arrayBuffer(),
      );
      if (!active) return;
      task = pdfjs.getDocument({
        data,
        isEvalSupported: false,
        enableXfa: false,
        useSystemFonts: true,
        disableFontFace: false,
      });
      loaded = await task.promise;
      if (active) setDocument(loaded);
      else loaded.destroy();
    })().catch((e) => {
      if (active && e.name !== "AbortError") onError(e.message);
    });
    return () => {
      active = false;
      controller.abort();
      if (loaded) loaded.destroy();
      else task?.destroy();
    };
  }, [job.id, token, onError]);
  useEffect(() => {
    if (!document) return;
    let active = true,
      render;
    document
      .getPage(page)
      .then((pdfPage) => {
        if (!active || !canvas.current) return;
        const viewport = pdfPage.getViewport({
          scale: ((96 / 72) * zoom) / 100,
        });
        if (viewport.width * viewport.height > 16_000_000)
          throw new Error("Preview exceeds the display budget. Reduce zoom.");
        const node = canvas.current;
        node.width = viewport.width;
        node.height = viewport.height;
        render = pdfPage.render({
          canvasContext: node.getContext("2d"),
          viewport,
        });
        return render.promise;
      })
      .catch((e) => {
        if (active && e.name !== "RenderingCancelledException")
          onError(e.message);
      });
    return () => {
      active = false;
      render?.cancel();
    };
  }, [document, page, zoom, onError]);
  return (
    <canvas
      ref={canvas}
      aria-label={`Generated PDF page ${page}`}
      role="img"
      className="pdf-canvas"
    />
  );
}

export default function Preview({ job, token }) {
  const [meta, setMeta] = useState(null),
    [error, setError] = useState("");
  const [page, setPage] = useState(1),
    [zoom, setZoom] = useState(100),
    [mode, setMode] = useState("pdf"),
    [sync, setSync] = useState(true);
  const left = useRef(null),
    right = useRef(null),
    syncing = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    setMeta(null);
    setError("");
    setPage(1);
    setMode("pdf");
    json(`/${job.id}/preview`, token, { signal: controller.signal })
      .then(setMeta)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, [job.id, token, job.version]);
  const scroll = (from, to) => {
    if (!sync || syncing.current || !to.current) return;
    syncing.current = true;
    const source = from.current,
      target = to.current;
    target.scrollTop =
      (source.scrollTop /
        Math.max(1, source.scrollHeight - source.clientHeight)) *
      (target.scrollHeight - target.clientHeight);
    target.scrollLeft =
      (source.scrollLeft /
        Math.max(1, source.scrollWidth - source.clientWidth)) *
      (target.scrollWidth - target.clientWidth);
    requestAnimationFrame(() => {
      syncing.current = false;
    });
  };
  if (!meta)
    return (
      <div className="preview-message" role="status">
        {error || "Checking available previews…"}
      </div>
    );
  const has = (kind) => meta.available_pages[kind]?.includes(page);
  const capture = mode === "side" ? "htm" : mode;
  return (
    <section aria-label="Document preview">
      <div className="review-notice">
        <ScanLine size={16} aria-hidden="true" />
        <span>Diagnostic preview · not a filing approval</span>
      </div>
      <div className="preview-toolbar">
        <div className="preview-mode-group" aria-label="Preview mode">
          {["pdf", "htm", "side", "overlay", "difference"].map((value) => (
            <button
              key={value}
              className={`btn btn-sm ${mode === value ? "btn-neutral" : "btn-ghost"}`}
              aria-pressed={mode === value}
              onClick={() => setMode(value)}
            >
              {
                {
                  pdf: "PDF",
                  htm: "HTM",
                  side: "Side by side",
                  overlay: "Print overlay",
                  difference: "Print diff",
                }[value]
              }
            </button>
          ))}
        </div>
        <div className="preview-nav">
          <button
            className="btn btn-ghost btn-sm btn-square"
            aria-label="Previous page"
            disabled={page <= 1}
            onClick={() => setPage((value) => value - 1)}
          >
            <ChevronLeft size={16} />
          </button>
          <label>
            Page{" "}
            <input
              aria-label="Page number"
              type="number"
              min="1"
              max={meta.pages}
              value={page}
              onChange={(event) =>
                setPage(
                  Math.max(
                    1,
                    Math.min(meta.pages, Number(event.target.value) || 1),
                  ),
                )
              }
            />{" "}
            of {meta.pages}
          </label>
          <button
            className="btn btn-ghost btn-sm btn-square"
            aria-label="Next page"
            disabled={page >= meta.pages}
            onClick={() => setPage((value) => value + 1)}
          >
            <ChevronRight size={16} />
          </button>
          <button
            className="btn btn-ghost btn-sm btn-square"
            aria-label="Zoom out"
            disabled={zoom <= 50}
            onClick={() => setZoom((value) => value - 25)}
          >
            <ZoomOut size={16} />
          </button>
          <span>{zoom}%</span>
          <button
            className="btn btn-ghost btn-sm btn-square"
            aria-label="Zoom in"
            disabled={zoom >= 200}
            onClick={() => setZoom((value) => value + 25)}
          >
            <ZoomIn size={16} />
          </button>
        </div>
      </div>
      {mode === "side" && (
        <label className="sync-toggle">
          <input
            type="checkbox"
            className="checkbox checkbox-xs"
            checked={sync}
            onChange={(event) => setSync(event.target.checked)}
          />
          <Columns2 size={14} /> Synchronize scrolling
        </label>
      )}
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
      <div className={`preview-grid ${mode === "side" ? "split" : ""}`}>
        {(mode === "pdf" || mode === "side") && (
          <div>
            <p className="pane-label">GENERATED PDF</p>
            <div
              className="page-scroll"
              ref={left}
              onScroll={() => scroll(left, right)}
            >
              <PdfPage
                job={job}
                token={token}
                page={page}
                zoom={zoom}
                dpi={meta.capture_dpi === 144 ? 144 : 96}
                onError={setError}
              />
            </div>
          </div>
        )}
        {mode !== "pdf" && (
          <div>
            <p className="pane-label">
              {mode === "overlay"
                ? "PDF / HTM PRINT OVERLAY"
                : mode === "difference"
                  ? "PRINT DIFFERENCES"
                  : "CHROMIUM HTM CAPTURE"}
            </p>
            <div
              className="page-scroll"
              ref={right}
              onScroll={() => scroll(right, left)}
            >
              {has(capture) ? (
                <Capture
                  job={job}
                  token={token}
                  kind={capture}
                  page={page}
                  zoom={zoom}
                />
              ) : (
                <p className="preview-message">
                  This capture has not been generated. Earlier validation must
                  finish before comparison artifacts are available.
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
