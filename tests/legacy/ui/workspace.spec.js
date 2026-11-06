import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFileSync } from "node:fs";
import path from "node:path";
const token = "a".repeat(40);
const seed = () =>
  JSON.parse(
    readFileSync(path.resolve("../../var/stage9/ui-seed.json"), "utf8"),
  );
const fixture = path.resolve(
  "../../tests/fixtures/06749LWD4_prelim_prospectus_automated.docx",
);
async function connect(page) {
  await page.goto("/");
  await page.getByLabel("API access token", { exact: true }).fill(token);
  await page.getByRole("button", { name: "Connect", exact: true }).click();
  await expect(page.getByText("Connected", { exact: true })).toBeVisible();
}
test("real API upload, independent batch jobs, theme, tab recovery and cancellation", async ({
  page,
}) => {
  await connect(page);
  await page.getByLabel("Choose DOCX files").setInputFiles([
    {
      name: "first.docx",
      mimeType:
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      buffer: readFileSync(fixture),
    },
    {
      name: "second.docx",
      mimeType:
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      buffer: readFileSync(fixture),
    },
  ]);
  await expect(page.getByText("2 documents selected")).toBeVisible();
  await page.getByRole("button", { name: "Start conversion" }).click();
  await expect(page.getByRole("table").getByRole("row")).toHaveCount(3);
  await expect(
    page.getByRole("button", { name: "Download ZIP" }),
  ).toBeDisabled();
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  expect(
    await page.evaluate(() =>
      Object.values(localStorage).some((value) => value.includes("aaaa")),
    ),
  ).toBe(false);
  await page.reload();
  await expect(page.getByText("Not connected", { exact: true })).toBeVisible();
  await page.getByLabel("API access token", { exact: true }).fill(token);
  await page.getByRole("button", { name: "Connect", exact: true }).click();
  await expect(page.getByRole("table").getByRole("row")).toHaveCount(3);
  await page.getByRole("button", { name: "Remove selected job" }).click();
  await page.getByRole("button", { name: "Remove job", exact: true }).click();
  await expect(page.getByRole("table").getByRole("row")).toHaveCount(2);
  await page.getByRole("button", { name: "Disconnect" }).click();
  await expect(page.getByRole("table")).toHaveCount(0);
});
test("actual failed native conversion exposes diagnostics and PDF without enabling ZIP", async ({
  page,
}) => {
  const job = seed();
  await connect(page);
  await page.getByText("Reopen a previous job").click();
  await page.getByLabel("Job ID", { exact: true }).fill(job.id);
  await page.getByRole("button", { name: "Open job", exact: true }).click();
  await expect(
    page.getByText("Review required", { exact: true }),
  ).toBeVisible();
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await expect(
    page.getByRole("button", { name: "Download ZIP" }),
  ).toBeDisabled();
  await page.getByRole("tab", { name: "Status & checks" }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(
    page.getByRole("tab", { name: "Preview & compare" }),
  ).toBeFocused();
  if (job.native_preview) {
    await expect(
      page.getByText("Diagnostic preview · not a filing approval"),
    ).toBeVisible();
    await expect
      .poll(() =>
        page.locator("canvas").evaluate((canvas) => {
          if (canvas.width <= 300) return false;
          const pixels = canvas
            .getContext("2d")
            .getImageData(0, 0, canvas.width, canvas.height).data;
          return pixels.some(
            (value, i) => i % 4 === 3 && value === 255 && pixels[i - 1] < 150,
          );
        }),
      )
      .toBe(true);
    await page
      .getByRole("button", { name: "Side by side", exact: true })
      .click();
    await expect(
      page.getByText("This capture has not been generated.", { exact: false }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
    await expect(page.getByText("125%", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Synchronize scrolling")).toBeChecked();
  } else
    await expect(
      page.getByText("Current diagnostic preview is unavailable"),
    ).toBeVisible();
});
test("invalid files and access failures are visible; uploads remain disabled", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("API access token", { exact: true }).fill("invalid");
  await page.getByRole("button", { name: "Connect", exact: true }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Valid bearer" }),
  ).toContainText("Valid bearer token required");
  await expect(
    page.getByRole("button", { name: "Choose documents" }),
  ).toBeDisabled();
  await connect(page);
  await page.getByLabel("Choose DOCX files").setInputFiles({
    name: "invalid.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("bad"),
  });
  await expect(
    page.getByRole("alert").filter({ hasText: "choose a DOCX" }),
  ).toContainText("choose a DOCX document");
});
test("keyboard dialog, responsive light/dark UI and automated accessibility", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Every detail matters." }),
  ).toBeVisible();
  let result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(result.violations).toEqual([]);
  await page.getByRole("button", { name: "How validation works" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../../var/stage9/desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(result.violations).toEqual([]);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../../var/stage9/mobile-dark.png",
    fullPage: true,
  });
});

test("drag and drop uses the same real batch admission", async ({ page }) => {
  await connect(page);
  const transfer = await page.evaluateHandle((data) => {
    const value = new DataTransfer();
    const bytes = Uint8Array.from(atob(data), (c) => c.charCodeAt(0));
    value.items.add(
      new File([bytes], "dropped.docx", {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      }),
    );
    return value;
  }, readFileSync(fixture).toString("base64"));
  await page
    .locator(".drop-zone")
    .dispatchEvent("drop", { dataTransfer: transfer });
  await expect(
    page.getByText("1 document selected", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Start conversion" }).click();
  await expect(
    page.getByRole("table").getByText("dropped.docx", { exact: true }),
  ).toBeVisible();
  await transfer.dispose();
});
