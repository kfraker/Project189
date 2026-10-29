// Combined coverage report: Python (app.py, db_migrations/) + page code (static/js/**)
// in ONE HTML view, with one total.
//
//   npm --prefix tools/coverage run report      →  coverage/all-html/index.html
//   npm --prefix tools/coverage run check       →  same, then FAIL if coverage dropped below
//                                                  baseline.json (used by CI after a full run)
//   npm --prefix tools/coverage run baseline    →  same, then record today's numbers as the
//                                                  new baseline (do this when coverage goes up)
//
// Inputs, written by a pytest run:
//   coverage/python.lcov                 (pytest-cov, every run)
//   coverage/js-raw/*.json               (browser tests; turned into coverage/js-html/ first)
// Python coverage arrives as lcov, so it's converted into the same (Istanbul) format
// the page-code report uses before the two are merged.
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import libCoverage from "istanbul-lib-coverage";
import libReport from "istanbul-lib-report";
import reports from "istanbul-reports";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..", "..");
const cov = (...p) => join(root, "coverage", ...p);
const mode = process.argv.includes("--check") ? "check"
           : process.argv.includes("--update-baseline") ? "baseline" : "report";
const BASELINE = join(here, "baseline.json");
const TOLERANCE = 0.5;   // percentage points of wobble allowed before a drop counts

// 1. Page code: refresh the JS report from the raw browser-test data.
if (existsSync(cov("js-raw"))) {
  const r = spawnSync(process.execPath, [join(here, "report-js.mjs")], { stdio: "inherit" });
  if (r.status !== 0) process.exit(r.status ?? 1);
}

const map = libCoverage.createCoverageMap({});
const jsJson = cov("js-html", "coverage-final.json");
if (existsSync(jsJson)) map.merge(JSON.parse(readFileSync(jsJson, "utf8")));
else console.log("No page-code coverage yet (run the browser tests).");

// 2. Python: lcov → Istanbul file coverage, one statement per measured line.
const pyLcov = cov("python.lcov");
if (existsSync(pyLcov)) {
  for (const record of readFileSync(pyLcov, "utf8").split("end_of_record")) {
    const sf = record.match(/^SF:(.+)$/m);
    if (sf) map.addFileCoverage(lcovToIstanbul(resolve(root, sf[1].trim()), record));
  }
} else console.log("No Python coverage yet (run pytest).");

if (map.files().length === 0) process.exit(0);

const dir = cov("all-html");
rmSync(dir, { recursive: true, force: true });
const context = libReport.createContext({ dir, coverageMap: map, defaultSummarizer: "nested" });
reports.create("html").execute(context);
reports.create("text-summary").execute(context);
console.log("Combined coverage (Python + page code): coverage/all-html/index.html");

// 3. Ratchet: line coverage may go up freely but must not drop.
const isPageCode = f => f.replace(/\\/g, "/").includes("/static/js/");
const linePct = files => {
  const summary = libCoverage.createCoverageSummary();
  for (const f of files) summary.merge(map.fileCoverageFor(f).toSummary());
  return Math.floor(summary.lines.pct * 10) / 10;
};
const now = {
  python: linePct(map.files().filter(f => !isPageCode(f))),
  javascript: linePct(map.files().filter(isPageCode)),
  combined: linePct(map.files()),
};
console.log(`Line coverage: python ${now.python}% · page code ${now.javascript}% · combined ${now.combined}%`);

if (mode === "baseline") {
  writeFileSync(BASELINE, JSON.stringify(now, null, 2) + "\n");
  console.log("Baseline updated: tools/coverage/baseline.json");
} else if (mode === "check") {
  const base = JSON.parse(readFileSync(BASELINE, "utf8"));
  const drops = Object.keys(base).filter(k => now[k] < base[k] - TOLERANCE);
  for (const k of Object.keys(base))
    console.log(`  ${k.padEnd(10)} baseline ${base[k]}%  now ${now[k]}%  ${drops.includes(k) ? "DROPPED" : "ok"}`);
  if (drops.length) {
    console.error(`Coverage dropped below the baseline (${drops.join(", ")}). Add tests for the new code, ` +
                  "or if the drop is intended, update the baseline with: npm --prefix tools/coverage run baseline");
    process.exit(1);
  }
}


function lcovToIstanbul(path, record) {
  const src = readFileSync(path, "utf8").split(/\r?\n/);
  const span = (start, end = start) => ({
    start: { line: start, column: 0 },
    end: { line: end, column: (src[end - 1] ?? "").length },
  });
  const fc = { path, statementMap: {}, s: {}, fnMap: {}, f: {}, branchMap: {}, b: {} };

  let i = 0;
  for (const [, line, hits] of record.matchAll(/^DA:(\d+),(\d+)/gm)) {
    fc.statementMap[i] = span(+line);
    fc.s[i++] = +hits;
  }

  const fnHits = Object.fromEntries(
    [...record.matchAll(/^FNDA:(\d+),(.+)$/gm)].map(([, hits, name]) => [name.trim(), +hits]));
  i = 0;
  for (const [, start, end, name] of record.matchAll(/^FN:(\d+),(?:(\d+),)?(.+)$/gm)) {
    fc.fnMap[i] = { name: name.trim(), decl: span(+start), loc: span(+start, +(end ?? start)), line: +start };
    fc.f[i++] = fnHits[name.trim()] ?? 0;
  }

  const branches = new Map();   // "line,block" → [taken counts]
  for (const [, line, block, , taken] of record.matchAll(/^BRDA:(\d+),(\d+),([^,]+),(.+)$/gm)) {
    const key = `${line},${block}`;
    if (!branches.has(key)) branches.set(key, []);
    branches.get(key).push(taken.trim() === "-" ? 0 : +taken);
  }
  i = 0;
  for (const [key, counts] of branches) {
    const line = +key.split(",")[0];
    fc.branchMap[i] = { type: "branch", line, loc: span(line), locations: counts.map(() => span(line)) };
    fc.b[i++] = counts;
  }
  return fc;
}
