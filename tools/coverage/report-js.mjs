// Page-code (JavaScript) coverage report.
//
// Browser tests save Chromium's raw V8 coverage for the app's own scripts to
// coverage/js-raw/ (see tests/browser/conftest.py). This turns it into:
//   coverage/js-html/index.html   line-by-line report for static/js/**
//   coverage/js.lcov              machine-readable copy for CI/Codecov
// Scripts no browser test loaded still appear, at 0%.
import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, rmSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..", "..");
const c8 = createRequire(import.meta.url).resolve("c8/bin/c8.js");
const rawDir = join(root, "coverage", "js-raw");
const htmlDir = join(root, "coverage", "js-html");

if (!existsSync(rawDir)) {
  console.log("No browser-test coverage found (coverage/js-raw/ missing) — run the browser tests first.");
  process.exit(0);
}

rmSync(htmlDir, { recursive: true, force: true });
const result = spawnSync(process.execPath, [
  c8, "report",
  "--temp-directory", rawDir,
  "--reports-dir", htmlDir,
  "--reporter", "html",
  "--reporter", "lcovonly",
  "--reporter", "json",        // full-detail copy, merged with Python by report-all.mjs
  "--reporter", "text-summary",
  "--all",
  "--src", "static/js",
  "--include", "static/js/**",
], { cwd: root, stdio: "inherit" });

if (result.status !== 0) process.exit(result.status ?? 1);
copyFileSync(join(htmlDir, "lcov.info"), join(root, "coverage", "js.lcov"));
console.log("Page-code coverage: coverage/js-html/index.html");
