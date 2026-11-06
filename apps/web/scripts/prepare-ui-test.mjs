import { execFileSync } from "node:child_process";
import path from "node:path";
const project = path.resolve("../..");
const python =
  process.env.CONVX_PYTHON ||
  path.join(
    project,
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
execFileSync(
  python,
  [
    path.join(project, "tests/e2e/write_fixture.py"),
    path.join(project, "var/t2ui-source.docx"),
  ],
  { cwd: project, stdio: "inherit", windowsHide: true },
);
