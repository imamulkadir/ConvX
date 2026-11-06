import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import path from "node:path";
import { readFileSync } from "node:fs";
const fixture = path.resolve("../../var/t2ui-source.docx");
async function ready(page) {
  await page.goto("/");
  await expect(page.getByText("Ready", { exact: true })).toBeVisible();
  await expect(
    page.getByLabel("API access token", { exact: true }),
  ).toHaveCount(0);
}

async function downloadZip(page, expectedFilename) {
  const event = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download ZIP", exact: true }).click();
  const download = await event;
  expect(download.suggestedFilename()).toBe(expectedFilename);
  expect(await download.failure()).toBeNull();
  const data = readFileSync(await download.path());
  expect(data.readUInt32LE(0)).toBe(0x04034b50);
  return data;
}

test("real EDGAR request renders in the running Next instance", async ({
  page,
}) => {
  test.setTimeout(240000);
  await ready(page);
  const response = await page.request.post("/api/v1/conversions", {
    headers: {
      origin: "http://127.0.0.1:3400",
      "content-type": "application/octet-stream",
      "x-convx-filename": "independent.docx",
      "x-convx-mode": "edgar",
    },
    data: readFileSync(fixture),
  });
  expect(response.status()).toBe(202);
  const id = (await response.json()).jobs[0].id;
  await expect
    .poll(
      async () => {
        const record = await (
          await page.request.get(`/api/v1/conversions/${id}`)
        ).json();
        return ["completed", "blocked", "failed"].includes(record.state);
      },
      { timeout: 180000, intervals: [250, 500, 1000] },
    )
    .toBe(true);
  const details = await (
    await page.request.get(`/api/v1/conversions/${id}/validation`)
  ).json();
  expect(details.complete, JSON.stringify(details.diagnostics)).toBe(true);
  expect(details.document_processing.sec_validation.passed).toBe(true);
  expect(
    details.document_processing.sec_validation.sec_acceptance_confirmed,
  ).toBe(false);
  expect(
    details.document_processing.edgar_visual_validation.checks_complete,
  ).toBe(true);
  await page.evaluate(
    (id) => sessionStorage.setItem("convx-jobs", JSON.stringify([id])),
    id,
  );
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Download ZIP" }),
  ).toBeEnabled();
  await downloadZip(page, "independent.zip");
  await page.getByRole("tab", { name: "Preview & compare" }).click();
  await page.getByRole("button", { name: "Side by side", exact: true }).click();
  await expect(
    page.getByText("This capture has not been generated.", { exact: false }),
  ).toHaveCount(0);
});

test("automatic internal service, real uploads, tab recovery and deletion", async ({
  page,
}) => {
  await ready(page);
  await page.getByLabel("Choose DOCX or PDF files").setInputFiles([
    {
      name: "first.docx",
      mimeType: "application/octet-stream",
      buffer: readFileSync(fixture),
    },
    {
      name: "second.docx",
      mimeType: "application/octet-stream",
      buffer: readFileSync(fixture),
    },
  ]);
  await expect(page.getByText("2 documents selected")).toBeVisible();
  await page.getByRole("button", { name: "Start conversion" }).click();
  await expect(page.getByRole("table").getByRole("row")).toHaveCount(3);
  await expect(
    page.getByRole("button", { name: "Download ZIP" }),
  ).toBeDisabled();
  await page.reload();
  await expect(page.getByRole("table").getByRole("row")).toHaveCount(3);
  await page.getByRole("button", { name: "Remove selected job" }).click();
  await page.getByRole("button", { name: "Remove job", exact: true }).click();
  await expect(page.getByRole("table").getByRole("row")).toHaveCount(2);
});

test("real native DOCX reaches authoritative analysis and PDF review", async ({
  page,
}) => {
  test.setTimeout(240000);
  await ready(page);
  await page.getByLabel("Choose DOCX or PDF files").setInputFiles(fixture);
  await page.getByRole("button", { name: "Start conversion" }).click();
  await expect(page.getByRole("button", { name: "Download ZIP" })).toBeEnabled({
    timeout: 180000,
  });
  await downloadZip(page, "t2ui-source.zip");
  await page.getByRole("tab", { name: "Status & checks" }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(
    page.getByRole("tab", { name: "Preview & compare" }),
  ).toBeFocused();
  await expect(
    page.getByText(/Diagnostic preview.*not a filing approval/),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.locator("canvas").evaluate((canvas) => {
        if (canvas.width <= 300) return false;
        const pixels = canvas
          .getContext("2d")
          .getImageData(0, 0, canvas.width, canvas.height).data;
        return pixels.some(
          (v, i) => i % 4 === 3 && v === 255 && pixels[i - 1] < 150,
        );
      }),
    )
    .toBe(true);
  await page.getByRole("button", { name: "Side by side", exact: true }).click();
  await expect(
    page.getByText("This capture has not been generated.", { exact: false }),
  ).toHaveCount(0);
});

test("invalid document is rejected by the real Python process", async ({
  page,
}) => {
  await ready(page);
  await page.getByLabel("Choose DOCX or PDF files").setInputFiles({
    name: "invalid.docx",
    mimeType: "application/octet-stream",
    buffer: Buffer.from("not a zip"),
  });
  await page.getByRole("button", { name: "Start conversion" }).click();
  await expect(page.getByText("INVALID_DOCX", { exact: true })).toBeVisible({
    timeout: 20000,
  });
  await expect(
    page.getByRole("button", { name: "Download ZIP" }),
  ).toBeDisabled();
});

test("direct PDF selection reaches shared analysis without Word export", async ({
  page,
}) => {
  test.setTimeout(240000);
  await ready(page);
  await page
    .getByLabel("Choose DOCX or PDF files")
    .setInputFiles(
      path.resolve(
        "../../tests/fixtures/06749LWD4_prelim_prospectus_automated.pdf",
      ),
    );
  const admitted = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith("/api/v1/conversions"),
  );
  await page.getByRole("button", { name: "Start conversion" }).click();
  expect((await admitted).status()).toBe(202);
  await expect
    .poll(() =>
      page.evaluate(
        () => JSON.parse(sessionStorage.getItem("convx-jobs") || "[]")[0],
      ),
    )
    .toMatch(/^[a-f0-9-]{36}$/);
  const id = await page.evaluate(
    () => JSON.parse(sessionStorage.getItem("convx-jobs"))[0],
  );
  await expect
    .poll(
      async () => {
        const record = await (
          await page.request.get(`/api/v1/conversions/${id}`)
        ).json();
        return ["completed", "blocked", "failed"].includes(record.state);
      },
      { timeout: 180000, intervals: [250, 500, 1000] },
    )
    .toBe(true);
  const status = await (
    await page.request.get(`/api/v1/conversions/${id}`)
  ).json();
  const details = await (
    await page.request.get(`/api/v1/conversions/${id}/validation`)
  ).json();
  expect(status.state, JSON.stringify(details.diagnostics)).toBe("completed");
  await expect(
    page.getByRole("button", { name: "Download ZIP" }),
  ).toBeEnabled();
  await downloadZip(page, "06749LWD4_prelim_prospectus_automated.zip");
  await expect(
    page.getByText("Accepted revisions", { exact: true }),
  ).toHaveCount(0);
  await page.getByRole("tab", { name: "Preview & compare" }).click();
  await expect(page.locator("canvas")).toBeVisible();
});

test("responsive light/dark workspace and keyboard help remain accessible", async ({
  page,
}) => {
  await ready(page);
  await page.setViewportSize({ width: 1440, height: 1100 });
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.getByRole("button", { name: "How validation works" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
});
