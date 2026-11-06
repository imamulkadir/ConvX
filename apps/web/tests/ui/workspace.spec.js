import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import path from "node:path";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { independentPdf } from "../helpers.mjs";
const fixture = path.resolve("../../var/t2ui-source.docx");
const reference = path.resolve(
  "../../tests/fixtures/06749LWD4_prelim_prospectus_automated.pdf",
);
const input = (page) =>
  page.getByLabel("Choose DOCX or PDF document", { exact: true });
const convert = (page) =>
  page.getByRole("button", { name: "Convert to HTM", exact: true });
const checkbox = (page) =>
  page.getByRole("checkbox", { name: "SEC EDGAR Compliance", exact: true });
async function ready(page) {
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "DOCX & PDF to HTM Converter",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Choose file", exact: true }),
  ).toBeEnabled();
}
async function start(page, file, mode = "standard") {
  await expect(input(page)).toBeEnabled();
  await input(page).setInputFiles(file);
  if (mode === "edgar") await checkbox(page).check();
  await expect(convert(page)).toBeEnabled();
  const request = page.waitForRequest(
    (r) => r.method() === "POST" && r.url().endsWith("/api/v1/conversions"),
  );
  await convert(page).click();
  expect((await request).headers()["x-convx-mode"]).toBe(mode);
  await expect
    .poll(() =>
      page.evaluate(() => sessionStorage.getItem("convx-current-job")),
    )
    .toMatch(/^[a-f0-9-]{36}$/);
  return page.evaluate(() => sessionStorage.getItem("convx-current-job"));
}
async function download(page, name) {
  await expect(
    page.getByRole("heading", { name: "Your ZIP is ready", exact: true }),
  ).toBeVisible({ timeout: 180000 });
  await expect(page.locator(".output-name")).toHaveText(name);
  const saved = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download ZIP", exact: true }).click();
  const result = await saved;
  expect(result.suggestedFilename()).toBe(name);
  expect(await result.failure()).toBeNull();
  expect(readFileSync(await result.path()).readUInt32LE(0)).toBe(0x04034b50);
  const id = await page.evaluate(() =>
    sessionStorage.getItem("convx-current-job"),
  );
  const project = path.resolve("../..");
  const python =
    process.env.CONVX_TEST_PYTHON ||
    path.join(
      project,
      ".venv",
      process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
    );
  const raw = execFileSync(
    python,
    [
      path.join(project, "tools/verify_download.py"),
      await result.path(),
      path.join(project, "var/t2ui", id),
    ],
    { cwd: project, windowsHide: true, encoding: "utf8", timeout: 65000 },
  );
  const checked = JSON.parse(raw);
  expect(checked.crc_verified).toBe(true);
  expect(checked.source_text_verified).toBe(true);
  expect(checked.download_filename).toBe(name);
  const evidence = path.join(project, "var/refactor-stage9/downloads");
  mkdirSync(evidence, { recursive: true });
  writeFileSync(
    path.join(evidence, id + ".json"),
    JSON.stringify(checked, null, 2) + "\n",
  );
}

test("minimal form, file validation, clear selection and keyboard checkbox", async ({
  page,
}) => {
  await ready(page);
  await expect(checkbox(page)).not.toBeChecked();
  await expect(convert(page)).toBeDisabled();
  await expect(page.locator("aside,table,[role=tablist]")).toHaveCount(0);
  await expect(
    page.getByLabel("API access token", { exact: true }),
  ).toHaveCount(0);
  await input(page).setInputFiles({
    name: "invalid.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("text"),
  });
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "choose a DOCX or PDF",
  );
  await expect(convert(page)).toBeDisabled();
  await input(page).setInputFiles({
    name: "empty.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.alloc(0),
  });
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "empty",
  );
  await input(page).setInputFiles({
    name: "large.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.alloc(20971521),
  });
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "exceeds",
  );
  await input(page).setInputFiles({
    name: "independent.pdf",
    mimeType: "application/pdf",
    buffer: independentPdf(),
  });
  await expect(convert(page)).toBeEnabled();
  await page.getByRole("button", { name: "Clear selection" }).focus();
  await page.keyboard.press("Enter");
  await expect(convert(page)).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Choose file", exact: true }),
  ).toBeFocused();
  await checkbox(page).focus();
  await page.keyboard.press("Space");
  await expect(checkbox(page)).toBeChecked();
  await expect(
    page.getByText(
      "EDGAR Mode — Uses only SEC-permitted HTML tags, attributes, and supported assets.",
      { exact: true },
    ),
  ).toBeVisible();
});

for (const mode of ["standard", "edgar"]) {
  test(`real ${mode} PDF conversion through the form and ZIP download`, async ({
    page,
  }) => {
    test.setTimeout(240000);
    await ready(page);
    const id = await start(
      page,
      {
        name: `independent-${mode}.pdf`,
        mimeType: "application/pdf",
        buffer: independentPdf(),
      },
      mode,
    );
    await download(page, `independent-${mode}.zip`);
    const details = await (
      await page.request.get(`/api/v1/conversions/${id}/validation`)
    ).json();
    expect(details.complete).toBe(true);
    expect(details.document_processing.mode).toBe(mode);
    expect(details.document_processing.packaging.document_filename).toBe(
      `independent-${mode}.${mode === "standard" ? "html" : "htm"}`,
    );
    if (mode === "edgar")
      await expect(
        page.getByText(
          "Local EDGAR checks passed. SEC filing acceptance is not confirmed.",
          { exact: true },
        ),
      ).toBeVisible();
    await page.reload();
    await download(page, `independent-${mode}.zip`);
    await expect(checkbox(page)).toBeChecked({ checked: mode === "edgar" });
    await page
      .getByRole("button", { name: "Convert another document", exact: true })
      .click();
    await expect(input(page)).toBeEnabled();
    await expect(checkbox(page)).not.toBeChecked();
    await expect
      .poll(async () =>
        (await page.request.get(`/api/v1/conversions/${id}`)).status(),
      )
      .toBe(404);
  });
}

for (const mode of ["standard", "edgar"]) {
  test(`real native DOCX ${mode} uses the selected mode and downloads`, async ({
    page,
  }) => {
    test.setTimeout(240000);
    await ready(page);
    const id = await start(page, fixture, mode);
    await download(page, "t2ui-source.zip");
    const report = (
      await (
        await page.request.get(`/api/v1/conversions/${id}/validation`)
      ).json()
    ).document_processing;
    expect(report.mode).toBe(mode);
    expect(report.source_unchanged).toBe(true);
    expect(report.revision_acceptance.after.total).toBe(0);
    expect(report.packaging.document_filename).toBe(
      mode === "standard" ? "t2ui-source.html" : "t2ui-source.htm",
    );
  });
}

test("direct reference PDF download and optional visual comparison", async ({
  page,
}) => {
  test.setTimeout(240000);
  await ready(page);
  await start(page, reference);
  await download(page, "06749LWD4_prelim_prospectus_automated.zip");
  await page.getByText("Preview and compare", { exact: true }).click();
  await expect
    .poll(() =>
      page.locator("canvas").evaluate(
        (canvas) =>
          canvas.width > 300 &&
          canvas
            .getContext("2d")
            .getImageData(0, 0, canvas.width, canvas.height)
            .data.some((v, i) => i % 4 === 0 && v < 150),
      ),
    )
    .toBe(true);
  await page.getByRole("button", { name: "Side by side", exact: true }).click();
  await expect(page.getByAltText("Converted document, page 1")).toBeVisible();
  await expect(
    page.getByAltText("Converted document, page 1"),
  ).toHaveJSProperty("complete", true);
});

test("unsupported EDGAR layout fails clearly without a download", async ({
  page,
}) => {
  test.setTimeout(240000);
  await ready(page);
  const id = await start(page, reference, "edgar");
  await expect(
    page.getByRole("heading", {
      name: "This document could not be converted",
      exact: true,
    }),
  ).toBeVisible({ timeout: 180000 });
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "Try Standard Mode",
  );
  await expect(
    page.getByRole("button", { name: "Download ZIP", exact: true }),
  ).toHaveCount(0);
  const report = (
    await (
      await page.request.get(`/api/v1/conversions/${id}/validation`)
    ).json()
  ).document_processing;
  expect(report.diagnostics.at(-1).code).toBe("EDGAR_CLIPPING_UNSUPPORTED");
});

test("invalid content is rejected and a running conversion can be cancelled", async ({
  page,
}) => {
  test.setTimeout(120000);
  await ready(page);
  await start(page, {
    name: "invalid.docx",
    mimeType: "application/octet-stream",
    buffer: Buffer.from("not a zip"),
  });
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "not a valid Word document",
    { timeout: 20000 },
  );
  await page
    .getByRole("button", { name: "Choose another document", exact: true })
    .click();
  const id = await start(page, fixture);
  await page
    .getByRole("button", { name: "Cancel conversion", exact: true })
    .click();
  await expect(input(page)).toBeEnabled();
  await expect
    .poll(async () =>
      (await page.request.get(`/api/v1/conversions/${id}`)).status(),
    )
    .toBe(404);
  await expect(
    page.getByRole("button", { name: "Download ZIP", exact: true }),
  ).toHaveCount(0);
});

test("drag and drop selects exactly one real document", async ({ page }) => {
  await ready(page);
  const data = await page.evaluateHandle((bytes) => {
    const transfer = new DataTransfer();
    transfer.items.add(
      new File([new Uint8Array(bytes)], "dropped.pdf", {
        type: "application/pdf",
      }),
    );
    return transfer;
  }, Array.from(independentPdf()));
  await page
    .locator(".upload-zone")
    .dispatchEvent("drop", { dataTransfer: data });
  await expect(page.getByText("dropped.pdf", { exact: true })).toBeVisible();
  await expect(convert(page)).toBeEnabled();
  await page
    .getByRole("button", { name: "Clear selection", exact: true })
    .click();
  const multiple = await page.evaluateHandle(() => {
    const transfer = new DataTransfer();
    for (const name of ["one.pdf", "two.pdf"])
      transfer.items.add(new File(["data"], name));
    return transfer;
  });
  await page
    .locator(".upload-zone")
    .dispatchEvent("drop", { dataTransfer: multiple });
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "one document at a time",
  );
  await expect(convert(page)).toBeDisabled();
});

test("a real network interruption preserves the current conversion", async ({
  page,
}) => {
  test.setTimeout(120000);
  await ready(page);
  const id = await start(page, {
    name: "reconnect.pdf",
    mimeType: "application/pdf",
    buffer: independentPdf(),
  });
  await page.context().setOffline(true);
  try {
    await expect(page.getByRole("main").getByRole("alert")).toContainText(
      "Connection interrupted",
      { timeout: 20000 },
    );
    expect(
      await page.evaluate(() => sessionStorage.getItem("convx-current-job")),
    ).toBe(id);
  } finally {
    await page.context().setOffline(false);
  }
  await download(page, "reconnect.zip");
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Your ZIP is ready", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => sessionStorage.getItem("convx-current-job")),
  ).toBe(id);
});

test("responsive light/dark form is keyboard accessible and visually captured", async ({
  page,
}, testInfo) => {
  await ready(page);
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const dark of [false, true]) {
      if (dark)
        await page
          .getByRole("button", { name: "Switch to dark mode", exact: true })
          .click();
      else if (
        await page
          .getByRole("button", { name: "Switch to light mode", exact: true })
          .count()
      )
        await page
          .getByRole("button", { name: "Switch to light mode", exact: true })
          .click();
      await expect(page.locator("html")).toHaveAttribute(
        "data-theme",
        dark ? "dark" : "light",
      );
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      const a11y = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      expect(a11y.violations).toEqual([]);
      await page.screenshot({
        path: testInfo.outputPath(
          `converter-${width}-${dark ? "dark" : "light"}.png`,
        ),
        fullPage: true,
      });
    }
  }
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to converter" }),
  ).toBeFocused();
});
