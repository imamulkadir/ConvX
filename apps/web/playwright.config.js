import { defineConfig } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);
export default defineConfig({
  testDir: "./tests/ui",
  timeout: 45000,
  workers: 1,
  fullyParallel: false,
  use: {
    baseURL: "http://127.0.0.1:3400",
    browserName: "chromium",
    trace: "retain-on-failure",
  },
  webServer: {
    command:
      "node scripts/prepare-ui-test.mjs && npm run build && npm run start -- --port 3400",
    url: "http://127.0.0.1:3400",
    env: {
      CONVX_PROJECT_ROOT: root,
      CONVX_TEMP_ROOT: path.join(root, "var/t2ui"),
      CONVX_PYTHON:
        process.env.CONVX_TEST_PYTHON ||
        path.join(
          root,
          ".venv",
          process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
        ),
      NEXT_TELEMETRY_DISABLED: "1",
    },
    timeout: 120000,
    reuseExistingServer: false,
  },
});
