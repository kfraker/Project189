# Changelog

## Unreleased

### Added
- `GET /health` for the upcoming daily uptime check. It opens a database connection and runs `SELECT 1`, returning `ok` (200) or `unavailable` (503) as `text/plain` with `Cache-Control: no-store`. It needs no sign-in, sets no cookie, and keeps failure details out of the response; they go to the server log (`app.logger.exception`). `tests/test_health.py` (8 tests) covers the healthy case, a refused connection, a failed query (the connection is still closed), HEAD requests, and no connection details, error text or cookies in the response.
- Daily uptime and error check. `.github/workflows/uptime.yml` runs `tools/uptime/check_site.py` once a day (13:17 UTC) and on demand, with an optional `base_url` input. The script uses only the standard library, doesn't follow redirects, and allows 30 seconds per request with no retry. It checks `/health` (200, `ok`), `/` and `/login` (200, with the sign-in button), `/static/style.css` (200), `/workouts` and `/weights` (302 to `/login`), `/api/weights` (401) and `/auth/google` (302 to `https://accounts.google.com/`). It exits 1 on any failure, so GitHub emails the owner, and logs only each check's status, never page content. `tests/test_uptime_check.py` (12 tests) runs it over real HTTP against the app on a local port (all checks pass; database down fails only `/health`; a missing page fails), against an unused port (every check fails), and against faked responses: a server error whose page content isn't echoed, a page missing its sign-in button, sign-in redirects to the wrong place, and exit codes.

### Changed
- Coverage baseline raised to the current full run: page code 75.4% → 76.0%, combined 76.7% → 77.4% (Python unchanged at 99.1%).

## 4.2.1 (2026-11-03)

### Fixed
- On phones, the profile picture picker was about 646px wide (four 116px pictures in a row plus padding), so on a 360–390px screen its Save button hung off the right edge. Below 720px wide the pictures now sit in a 2×2 grid with less padding, and the picker is capped at the screen width minus 32px.
- `tools/coverage/check_flows.py` crashed on a Windows console (cp1252) printing the table's ✅. It now writes UTF-8.

### Added
- Phone and tablet touch tests for the 10 flows that only had desktop tests (`tests/browser/test_mobile.py`, 30 tests): logging out, setting the goal weight, editing, deleting and noting a weigh-in from the table, deleting a workout, switching to kilograms, choosing a profile picture, filling in the fight card, and reading Insights. Each runs at 360×640, 390×844 and 820×1180 with touch. Flow coverage is now 57 of 57 flow-device pairs (100%); baseline and `docs/user-flows.md` refreshed. Two first-run failures: the profile picture picker (a real bug, fixed above) and a test mistake (the goal test didn't confirm overwriting the already-saved goal).
- User flow coverage. `tests/flows.toml` lists 19 user flows; browser tests name the flows they prove with `@pytest.mark.flow`, and `tests/flow_coverage.py` records each passing test's flows and device (desktop, or phone/tablet by the emulated screen's shorter side) to `coverage/flows.json`. `tools/coverage/check_flows.py` prints the flow-by-device table and gaps (also to the GitHub Actions run summary), writes `docs/user-flows.md` with `--update`, and fails CI if a pair in `tools/coverage/flow_baseline.json` loses its test. A test naming an unlisted flow stops the run at collection. Starting point: 37 of 57 pairs (65%), with 10 flows untested on phone and tablet. 71 existing tests tagged, plus 11 tests for the tooling.

## 4.2.0 (2026-11-03)

### Fixed
- On phones, the sign-in card filled the screen edge to edge: its padding was added on top of `width: min(360px, 90vw)`. Its pop-in bounce then briefly overflowed the screen, which made `test_login_page_fits` fail intermittently in CI depending on when it measured. The card now uses `box-sizing: border-box`, and the test waits for the animation to finish and requires a side margin.
- The server counted days from its own UTC date, which is already tomorrow for US visitors from 7–8pm. Every evening the Weigh-ins streak dropped to 0, and the 7-day average and Home's weekly calorie burn shifted a day. Home and Weigh-ins now send the visitor's date (`?today=YYYY-MM-DD`) with `/api/home-stats` and `/api/weight/stats`, and the server uses it when it's within a day of its own (`_visitor_today()`), otherwise its own date (`_server_today()`).
- East of UTC (e.g. Europe, Asia), the Weigh-ins table froze the page: `addDays` turned local midnight into a UTC date, so adding a day returned the same day and `dateRange` never ended. The daily chart, 7-day average line and weekly chart/table (rolling and calendar weeks) were also a day off there. All 11 `toISOString()` date conversions in `weights.js` now use a new local-date helper, `isoDate()` in `shell.js`.
- Insights "Largest Weekly Loss" missed a 7-day window spanning the clocks going back, and "Avg Daily Fluctuation" skipped a day pair spanning the clocks going forward, because both treated a day as exactly 24 hours. They now count calendar days with `daysApart`.
- Workouts "this week" and the date-range filter subtracted 24-hour multiples, so late in the evening in a clock-change week they started a day off. They now use a new `daysAgoISO()` helper.
- On short screens (700px tall or less), Home's Log Workout window lacked the compact layout the Workouts page has, so on a small phone "+ Add Activity" started below the visible part of the window. Home now has the same `@media (max-height: 700px)` rules.

### Added
- Server tests for the visitor's date (`tests/test_visitor_today.py`, 11 tests), with the server's date pinned, and browser tests that both pages send it.
- Time zone browser tests (`tests/browser/test_time_zones.py`, 23 tests): the Weigh-ins charts, average line, weekly views and table in Honolulu, New York, Berlin and Tokyo on a fixed date with history spanning both clock changes, plus clock-change tests for Insights and Workouts. Each failed before its fix.
- ESLint rule banning `toISOString()` in page code, pointing to `isoDate()`.
- Phone and tablet browser tests (`tests/browser/test_mobile.py`, 47 tests): 360×640, 390×844 and 820×1180 with touch, plus 640×360 landscape. They cover sideways overflow, tap targets, windows, touch logging and the custom cursor. Draft findings triaged: the cursor-after-tap failures were already fixed by the 4.1.0 touch change, and 9 failures were mistakes in the draft (wrong button ids, a heading that's never shown).
- Performance budget in CI (`tests/browser/test_performance_budget.py`). Each page loads with an empty cache under emulated 4G (10 Mbps, 40 ms), and fails on bytes received, request count, or Largest Contentful Paint over 2.5 s. Limits are about 20% above sizes measured on 2026-11-02. An unmeasured warm-up load runs first, so the test server's cold start (2.9 s on the first page) isn't counted. Two tests prove the gate trips: an oversized image and a slow network.

## 4.1.5 (2026-11-02)

### Security
- Updated Pillow, used only by the dev-time image tool (`tools/images`), from 12.3.0 to 13.0.0 to resolve 41 Dependabot advisories. It was pinned in 4.1.4 without checking its advisories. Rebuilt images are byte-identical.

## 4.1.4 (2026-11-02)

### Fixed
- Insights streaks compared dates as exactly 24 hours apart, so a 23 or 25-hour day around a clock change reset them. They now count calendar days (`daysApart` in `shell.js`), with tests pinned to both clock changes.
- Home showed the plates' shadows and text before their image loaded. Plates now stay hidden until it's downloaded and decoded (`Image.decode()`), with a 3-second limit so they can't stay hidden.

### Changed
- Home's first download fell from 4.57 MB to 0.69 MB. Profile pictures are 256px instead of 1024px, the plate and backgrounds are WebP, and hidden images (`loading="lazy"`) no longer download until shown.
- Static files now have cache headers: a year for URLs with a content hash, a day for other images. Debug mode is excluded.

### Added
- `tools/images/optimize_images.py` builds the served images from full-size originals, now kept in `design/originals/` and not deployed.
- Tests for the plate reveal, skipped downloads, cache headers, referenced images existing, and image size limits.

## 4.1.3 (2026-11-02)

### Added
- Ruff for Python, and ESLint and Prettier for page code, enforced in CI. Dependabot watches the new tools.
- Browser test for clicking a Weigh-ins table row to edit it, a flow that had no test.

### Changed
- Formatted all Python and page code, with no behavior change. CSS and templates aren't formatted.
- Marked the static file version hash as non-security (`usedforsecurity=False`). It only detects changed files.
- Reset the page-code coverage baseline from 84.5% to 75.4%, and combined from 86.1% to 76.7%. Formatting put statements on separate lines, which exposed that compressed lines had been counting as covered when a test touched any part of them. No tests were removed.

### Removed
- Dead code: `startEdit` (inline cell editing, long replaced by the weigh-in window), the `showTableConfirm` window only it used, and an unused Insights calculation.

## 4.1.2 (2026-11-01)

### Security
- Updated Python dependencies to resolve Dependabot alerts: Authlib 1.7.2 to 1.9.1, certifi to 2026.10.23, cryptography to 50.0.2, joserfc to 1.7.7, urllib3 to 2.8.0, Werkzeug to 3.1.9, plus routine updates to the other packages.
- Pinned `minimatch` to a fixed version in the dev-only coverage tools through an npm override. A moderate `glob` advisory remains in those tools; they aren't deployed, and npm's only fix would downgrade `c8` by three major versions.

### Changed
- Updated GitHub Actions to current versions (`checkout`, `setup-python`, `setup-node`, `upload-artifact`, `codecov-action`).
- Held `pyee` at 14.0.0, as Playwright requires, and told Dependabot to leave it.
- README and docs now describe the CI/CD pipeline: protected `main`, required `test` check, and Vercel Deployment Checks. Proven with three drills: a failing pull request was blocked, a passing release was held until tests finished, and a failure on `main` left production unchanged.

## 4.1.1 (2026-11-01)

### Fixed
- Weigh-in and weight card windows moved focus 50ms after opening, in `home.js` and `weights.js`, so input entered in that gap could be lost and Save would do nothing. Focus now moves as the window opens. This also removes an intermittent CI failure.

### Added
- Regression test for the focus race, and a user flow coverage story and decision in the docs.
- `main` branch protection (pull request and the `test` check required, admins included) and a Vercel Deployment Check on `test`.

## 4.1.0 (2026-10-31)

### Added
- Neon `dev` branch as a database sandbox for local development and `dev` previews; Vercel `DATABASE_URL` scoped to the `dev` preview branch as a Secret.
- `APP_ENV=sandbox` setting and `templates/_env_badge.html`: SANDBOX badge, plus a PRODUCTION DATA warning in debug mode without the setting. No badge in production.
- `tools/sandbox/seed_mock_data.py`: fills an account with mock data through the API; refuses to run unless `APP_ENV=sandbox`, and off Vercel only.
- `docs/requirements/roadmap.md` (epics, stories, acceptance criteria) and `docs/decisions.md`.
- README sections for the sandbox, and for releases and rollback (rollback and return tested on production, v4.0.0 to v3.3.2 and back).
- MIT `LICENSE`.
- `.github/dependabot.yml`: weekly grouped update checks for pip, npm and GitHub Actions, targeting `dev`.
- Tests: `tests/test_env_badge.py`, `tests/test_sandbox_seed.py`, and a browser test for the badge (610 tests in total).

### Changed
- Neon's Vercel integration now covers Production and Development only, so previews no longer receive production credentials. Previews from other branches have no database and fail safely.
- Registered the `dev` preview address as a Google sign-in callback.
- Turned on Dependabot alerts and security updates for the repo.
- Repository homepage now points to https://sweatequity.kfraker.dev.
- `.coveragerc` omits `tools/`, which was counting developer tools as app code.

### Removed
- Temporary `demo` and `test` schemas from the production database. Row counts in `public` verified unchanged.

## 4.0.0 (2026-10-31)

A major release. The front end now runs on a new page architecture, and the project gained a CI pipeline and an automated test suite that runs on every push.

### Architecture
- **In-page navigation.** The shell (header, footer, menus, custom cursor) loads once, and nav clicks swap in only the parts of the page that change. The server still renders every page in full, so refreshes, bookmarks and direct links work as before, and anything unexpected falls back to a normal page load.
- **Page lifecycle.** Each page now starts through `registerPage()` and cleans up after itself when left: event listeners, charts, observers, page-level globals, and responses that arrive too late.
- **History and accessibility.** The address bar, tab title and active nav button stay in step, including with Back and Forward. Focus moves to the new content, and the page name is announced to screen readers.
- **Transitions.** Short fades between pages and a cross-fade between backgrounds, switched off for visitors who prefer reduced motion.
- **Script organization.** Page scripts moved out of the templates into versioned JavaScript files, and Chart.js loads only on the page that needs it.

### CI pipeline and automated testing
- **591 tests**, up from about 390 server-only tests: 435 API and server tests, plus 156 Playwright tests running the real app in Chromium.
- **Browser coverage** of user flows on every page, the shared shell, page lifecycle (each page restarted 20 times with nothing piling up), and navigation (rapid clicks, Back/Forward, fallbacks). A 35-step stress test checks that pages reached in place look identical to a fresh load.
- **Automatic failure on page errors.** Any browser test fails on a JavaScript error, failed request or error response.
- **New CI pipeline.** Every push to `dev` and `main` runs on GitHub Actions: it installs the app, runs the full suite in Chromium against a throwaway Postgres database, reports coverage and enforces the coverage guard, and attaches screenshots and traces when a browser test fails.
- **Tracked coverage.** Python and JavaScript coverage are reported to Codecov, with 99.1% of Python lines, 84.5% of JavaScript lines and 86.1% combined. CI fails if coverage drops more than 0.5 points below the recorded baseline.
- **Test isolation.** Tests run in a separate database schema, and the live test server refuses all requests unless that schema is active.

### Design
- New backgrounds: a speedboat on Biscayne Bay at dusk (Home and sign-in), a boxing gym at sunrise (Weigh-ins), and a garage gym on a Miami afternoon (Workouts).
- An open-hand cursor over the Home weight plates and the note resize handle, matched to the profile picture.
- Removed about 21 MB of unused images.
- The health bar HUD and its settings are hidden for now, because its position and size don't hold up across screen widths.

### Fixed
- Windows no longer flashes its white cursor over the custom one on nav clicks.
- In the Log Workout delete checklist, ticked workouts are now the ones deleted. Previously it deleted the unticked ones.
- Saving Settings on the Workouts page no longer blanks the table.
- The Log Workout window can no longer end up under the header and footer on laptop screens, which made Save unclickable.
- "Unsaved changes" prompts now offer a working way to close without saving.
- Weigh-ins table view now gets its intended styling.
- The "Coming Soon" tip on Nutrition no longer covers the other nav buttons.
- The custom cursor no longer appears on touchscreens after a tap.

### Documentation
- Added this changelog, screenshots and a roadmap, and brought the README's setup, stack and project structure up to date.

## 3.x (July to October 2026)
- **3.3.2:** moved the chart's "max data" info icon next to the title.
- **3.3.1:** nav flicker fix, streak fixes, hover tooltips removed.
- **3.3.0:** moved the database from SQLite to Postgres on Neon.
- **3.2.0:** Google sign-in and per-user data isolation.
- **3.1.0:** hand-rolled database migration system.
- **3.0.0:** header navigation redesign and README overhaul.

## 2.x (July 2026)
- **2.8.x:** shared base template, Menu window, Quick Add, Weigh-ins rebrand, unified date range picker.
- **2.7.0:** Workouts filter menu and custom date ranges.
- **2.6.0:** Workouts staging workflow and day notes.
- **2.5.0:** goal modes: Lean Machine and Muscle Monster.
- **2.4.x:** accessibility passes against WCAG 2.2 Level AA.
- **2.3.x:** note-only rows, delete options, responsive tables.
- **2.1.0 to 2.2.x:** Weekly Summary chart, Settings toggles, note editor.
- **2.0.0:** health bar HUD and chart overlays.

## 1.x (June to July 2026)
- **1.4.0:** Insights window and goal date prediction.
- **1.3.x:** preferences saved on the server, cleaner custom cursors.
- **1.2.0:** Fight Card and themed date pickers.
- **1.1.0:** profile button and saved default settings.
- **1.0.0:** first release: weight logging, charts, table, custom cursors. Earlier prototype commits used their own `v2` to `v5` labels, unrelated to these version numbers.
