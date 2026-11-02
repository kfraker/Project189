# Decision log

Key decisions behind Sweat Equity and why they were made. Newest first. Earlier entries were written up afterward from project history.

## Reset coverage to the honest number after formatting (2026-11-02)
**Decision:** lower the page-code coverage baseline from 84.5% to 75.4%, and say why, rather than exclude code or adjust the measure to keep the higher figure.
**Why:** compressed JavaScript let one test mark a whole long line as covered. Formatting put statements on their own lines, so the new number shows what the tests really run. The tests themselves didn't change.

## Gate production deploys with Vercel Deployment Checks and branch protection (2026-11-01)
**Decision:** `main` accepts changes only through pull requests that pass the tests, including from admins, and Vercel holds each production deploy until the `test` check passes on `main`.
**Why:** a failed test had gone live during the 4.1.0 release. This needed less setup than having GitHub Actions deploy, and the two layers cover different failures: one stops bad code merging, and the other stops anything that fails only after merging. The docs say CI/CD now because all of this was proven with deliberate failures.

## Track user flow coverage alongside code coverage (2026-11-01)
**Decision:** keep a list of every user flow, linked to the tests that prove it on each device, and report it on every run.
**Why:** code coverage shows which lines ran, not whether a user's goal works. It can look excellent while a whole flow or device goes untested, as phone sizes did here.

## Keep the repo public, under the MIT license (2026-10-31)
**Decision:** the code stays public and open source.
**Why:** this project is a portfolio showcase, so reviewers should be able to see the code, tests, CI and requirements, not just the finished site. Real data isn't in the repo, so being public doesn't expose it.

## Demo visitors will get their own separate database (2026-10-31, planned)
**Decision:** public demo accounts will live in a separate, empty database, not alongside real accounts.
**Why:** even if a per-user check had a bug, a public visitor could only ever reach other temporary demo accounts. Keeping them in the production database was simpler but relied entirely on those checks.

## Each demo visitor gets a private, temporary account (2026-10-31, planned)
**Decision:** one click creates a fresh account full of mock data, wiped when the visitor leaves or logs out.
**Why:** a shared account would show visitors each other's edits, and a read-only one would stop them trying the best part of the app.

## Requirements are written for new work only (2026-10-31)
**Decision:** requirements live in the repo from now on, starting with upcoming work. Past work isn't back-written.
**Why:** requirements written after the fact wouldn't reflect how the work was really done. The changelog and this log cover the history.

## Hide the health bar until it's redesigned (2026-10-30)
**Decision:** the health bar and its settings are hidden for everyone, with the code kept.
**Why:** its position and size didn't hold up across screen widths: it could cover the weight plates or shrink until unreadable. New art wouldn't fix that, so it needs a proper redesign or removal.

## Use a Neon branch as the database sandbox (2026-10-31)
**Decision:** local development and `dev` previews use a Neon branch, with a badge showing which database is in use.
**Why:** both used to share the production database. A branch is a full, resettable copy that's created instantly, and it gives a realistic place to test. Neon's automatic per-preview branches were turned down in favor of one predictable sandbox.

## Call it CI, not CI/CD, until deploys wait for tests (2026-10-30)
**Decision:** public docs described a CI pipeline only until deploys were gated, which happened on 2026-11-01.
**Why:** Vercel was deploying `main` whether or not tests passed, so "CI/CD" wouldn't have been accurate.

## Keep server-rendered pages, and swap them in place (2026-10-28)
**Decision:** the header, footer and menus load once and nav clicks swap in only what changes, while the server still renders complete pages. Any unexpected response falls back to a normal page load.
**Why:** every nav click was a full reload, which made Windows flash its white cursor over the custom one and rebuilt an unchanging shell. A full front-end framework rewrite wasn't needed, and this keeps refreshes, bookmarks and direct links working.

## Build the test safety net before the migration (2026-10-28)
**Decision:** the browser tests and coverage tracking came first, then the navigation work.
**Why:** the migration was almost entirely page code, and nothing tested that yet. Doing it in this order gave the riskiest change a safety net, and the tests found real bugs along the way.

## Use Playwright for browser tests, and measure JavaScript coverage (2026-10-28)
**Decision:** Playwright with pytest, using Chromium's built-in coverage for page code.
**Why:** it plugs into the existing test runner, waits for elements automatically, records traces on failure and needs no build step for coverage. Selenium needs more glue, and Cypress would have meant a second, JavaScript-only test stack.

## Guard coverage with a ratchet, not a fixed target (2026-10-28)
**Decision:** CI fails if coverage drops more than 0.5 points below a recorded baseline.
**Why:** it stops quality slipping without encouraging tests written just to hit a number.

## Move from SQLite to Postgres on Neon (2026-07-17)
**Decision:** replace the local SQLite file with hosted Postgres.
**Why:** SQLite served the early local-only app well, but Vercel's serverless hosting has no persistent disk to keep a database file on. Neon offers serverless Postgres with a free tier and a Vercel integration.
