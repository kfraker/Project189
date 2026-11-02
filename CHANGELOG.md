# Changelog

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
