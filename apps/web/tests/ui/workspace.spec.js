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

test("automatic internal service, real uploads, tab recovery and deletion", async ({
  page,
}) => {
  await ready(page);
  await page.getByLabel("Choose DOCX files").setInputFiles([
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

test("real isolated native converter preserves the current reference failure and PDF review", async ({
  page,
}) => {
  test.setTimeout(120000);
  await ready(page);
  await page.getByLabel("Choose DOCX files").setInputFiles(fixture);
  await page.getByRole("button", { name: "Start conversion" }).click();
  await expect(
    page.getByText("PDF_REFERENCE_REQUIRED", { exact: true }).first(),
  ).toBeVisible({ timeout: 90000 });
  await expect(
    page.getByRole("button", { name: "Download ZIP" }),
  ).toBeDisabled();
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
  ).toBeVisible();
});

test("invalid document is rejected by the real Python process", async ({
  page,
}) => {
  await ready(page);
  await page.getByLabel("Choose DOCX files").setInputFiles({
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
