export const stages = [
  ["uploaded", "Uploaded"],
  ["validating", "Validating"],
  ["accepting_revisions", "Accepting revisions"],
  ["generating_pdf", "Generating PDF"],
  ["analyzing_pdf", "Analyzing PDF"],
  ["generating_htm", "Generating HTM"],
  ["preparing_assets", "Preparing assets"],
  ["validating_sec", "SEC validation"],
  ["comparing_formatting", "Comparing formatting"],
  ["packaging_zip", "Packaging ZIP"],
  ["completed", "Completed"],
];
export const terminal = new Set([
  "completed",
  "failed",
  "blocked",
  "expired",
  "cancelled",
]);
export const resumable = new Set([
  "PIPELINE_NOT_AVAILABLE",
  "PDF_RENDERER_UNAVAILABLE",
  "PDF_REFERENCE_REQUIRED",
  "LAYOUT_ENGINE_NOT_AVAILABLE",
  "HTML_ENGINE_NOT_AVAILABLE",
  "SEC_ENGINE_NOT_AVAILABLE",
  "VISUAL_ENGINE_NOT_AVAILABLE",
  "VISUAL_BROWSER_UNAVAILABLE",
  "PACKAGING_ENGINE_NOT_AVAILABLE",
]);
export function stageIndex(job) {
  if (job.state === "completed") return stages.length - 1;
  const aliases = {
    queued: "uploaded",
    validating_docx: "validating",
    validating_pdf: "generating_pdf",
    normalizing_assets: "preparing_assets",
  };
  return stages.findIndex(([key]) => key === (aliases[job.stage] || job.stage));
}
export function bytes(value) {
  return value >= 1048576
    ? `${(value / 1048576).toFixed(1)} MB`
    : `${Math.ceil(value / 1024)} KB`;
}
export function validateSelection(files, limits) {
  const valid = [],
    errors = [];
  for (const file of files) {
    if (!file.name.toLowerCase().endsWith(".docx"))
      errors.push(`${file.name}: choose a DOCX document.`);
    else if (!file.size) errors.push(`${file.name}: this file is empty.`);
    else if (file.size > limits.max_upload_bytes)
      errors.push(`${file.name}: exceeds ${bytes(limits.max_upload_bytes)}.`);
    else if (valid.length >= limits.max_batch_files)
      errors.push(`${file.name}: batch limit is ${limits.max_batch_files}.`);
    else valid.push(file);
  }
  return { valid, errors };
}
export function downloadName(header, fallback) {
  const encoded = /filename\*=utf-8''([^;]+)/i.exec(header || "");
  let name = fallback;
  try {
    if (encoded) name = decodeURIComponent(encoded[1]);
  } catch {
    /* Safe fallback. */
  }
  return name.replace(/[\\/\x00-\x1f\x7f]/g, "_");
}
