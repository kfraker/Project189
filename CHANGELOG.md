# Changelog

## Unreleased

### Database sandbox
- Added a separate sandbox database, so development and testing no longer touch real data.
- The local version of the app now runs on the sandbox.
- Preview versions of the site from the `dev` branch now run on the sandbox too, and no longer have access to the production database.
- Previews from any other branch now have no database at all, so they can't reach real data by accident.
- Signing in with Google now works on the `dev` preview site.
- Added a SANDBOX badge that shows whenever the app is running on the sandbox, including on the sign-in page.
- Added a loud PRODUCTION DATA warning for anyone running the app in debug mode without the sandbox setting, so real data doesn't get edited by mistake.
- Visitors to the live site see neither of these labels.
- Added a command that fills a sandbox account with about four months of realistic weigh-ins, workouts and notes. It refuses to run anywhere but the sandbox.
- Removed leftover temporary test data from the production database. Real data wasn't changed.

### Documentation
- Added instructions for setting up the sandbox, filling it with mock data and resetting it.

### Testing
- Added tests for the sandbox badge, the production warning, and the mock data command's safety checks.
- Fixed test coverage reports counting developer tools as if they were part of the app.

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
