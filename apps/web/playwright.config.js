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
  webServer: [
    {
      command: `"${path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python")}" tests/e2e/serve_api.py`,
      cwd: root,
      url: "http://127.0.0.1:8766/api/v1/health",
      timeout: 120000,
      reuseExistingServer: false,
    },
    {
      command: "npm run build && npm run start -- --port 3400",
      url: "http://127.0.0.1:3400",
      env: {
        CONVX_API_URL: "http://127.0.0.1:8766",
        NEXT_TELEMETRY_DISABLED: "1",
      },
      timeout: 60000,
      reuseExistingServer: false,
    },
  ],
});
