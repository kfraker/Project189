# Roadmap and requirements

Upcoming work as epics and stories, in the order it's planned. Each story is done when its acceptance criteria are met. Finished work moves to the [changelog](../../CHANGELOG.md), and the reasoning behind big choices is in the [decision log](../decisions.md).

Sizes: **S** is about one sitting, **M** is a couple of sittings.

## Epic 1: Foundations
*Status: done, released in v4.1.0.*

- **1.1 Repo basics** (S). Done: the repo links to the live site and is licensed under MIT.
- **1.2 Dependency alerts** (S). Done: alerts are on, and weekly update checks target `dev` so updates pass the full test suite first.
- **1.3 Documented rollback** (S). Done: the README has steps for undoing a bad release, tested on the live site.
- **1.4 Decisions and requirements in the repo** (S). Done: this file and the decision log are published, and we keep them current.

## Epic 2: Complete the CI/CD pipeline
*Status: done.*

- **2.1 Confirm the approach** (S). Done: Vercel's Deployment Checks is available on this hosting plan.
- **2.2 Protect the main branch** (S). Done: changes reach `main` only through a pull request that has passed the test suite, and a direct push was tested and refused.
- **2.3 Deploys wait for tests** (M). Done: the `test` check is required before production goes live.
- **2.4 Prove and document it** (S). Done: a failing pull request couldn't merge, a passing release went live only after its tests finished, a failure after merging left the live site unchanged, and the docs are updated.

## Epic 3: Consistent code
*Status: done.*

- **3.1 Formatting and lint** (M). Done: the existing code is cleaned up with no behavior change, and CI fails on new violations.

## Epic 4: Fast and works on every screen
*Status: in progress (4.4 left).*

- **4.1 Fast first load** (M). Done: Home's download fell from 4.57 MB to 0.69 MB, images are sized to how they're displayed, unneeded downloads are gone, static files are cached, and plates appear whole.
- **4.2 Performance budget** (S). Done: CI fails if a page's download size, request count or Largest Contentful Paint (2.5 s on emulated 4G) goes past its limit, and tests prove the check trips.
- **4.3 Phone and tablet tests** (M). Done: key flows run at two phone sizes, a tablet and a sideways phone with touch, in Chromium's emulation. The one bug found, Home's Log Workout window not being compact on small phones, is fixed.

- **4.4 User flow coverage** (M). Code coverage shows that lines ran, not that a user's goal works. **Done when:** every user flow is listed and tagged to the tests that prove it, by device; each run reports flow coverage with the gaps named; and CI fails if a test names an unlisted flow or a covered flow loses its test.

- **4.5 Dates in every time zone** (M). A streak bug appeared when the clocks changed, and CI runs in UTC so it couldn't catch it. **Done when:** date handling is reviewed in the browser and on the server, and key date flows are tested across time zones and clock changes.
  - **4.5a Page dates.** Done: the browser works out every calendar date in the visitor's own time zone. This fixed a Weigh-ins freeze east of UTC, charts and weekly views a day off there, and three clock-change slips. It's tested in four time zones, and a lint rule stops the UTC conversion coming back.
  - **4.5b The server's "today"** (S). Done: Home and Weigh-ins send the visitor's date with their stats requests, and the server uses it when it's within a day of its own. This fixed the Weigh-ins streak dropping to 0 every US evening. Tests pin the server's date to cover the evening case.

## Epic 5: Keeping it running
- **5.1 Uptime checks and error alerts** (S). **Done when:** an outage or a burst of errors sends an alert, and that's been tested.
- **5.2 Tested backups** (S). **Done when:** the backup approach is written down and a restore has been proven on a throwaway copy.

## Epic 6: Accessibility checks
- **6.1 Automated accessibility tests** (M). **Done when:** every page is checked automatically against WCAG 2.2 AA in CI, and issues found are fixed or deliberately deferred.

## Epic 7: Ready for public visitors
- **7.1 Security review and hardening** (M). **Done when:** a review is complete and its findings are resolved, including input limits, secure cookies and security headers.
- **7.2 Hosting secrets** (S). **Done when:** database credentials are rotated and stored as hidden secrets.

## Epic 8: Demo mode
*Goal: anyone can try the full app in one click, with no sign-up.*

- **8.1 A separate demo database** (S). **Done when:** tests prove a demo session can't reach the main database, and the main database holds no demo data.
- **8.2 Temporary accounts** (S). **Done when:** demo accounts are marked as temporary, and real accounts are unaffected.
- **8.3 Realistic mock data** (M). About four months of history ending yesterday: steady progress with a plateau, an unbroken recent streak, varied workouts and notes, and today left open to log. **Done when:** every page looks fully used, and setup takes about 2 seconds or less.
- **8.4 Start a demo** (S). **Done when:** two visitors get separate accounts and can't see each other's changes, crawlers can't create accounts, and a limit on active demos gives a friendly message when reached.
- **8.5 End and wipe** (M). Log out wipes the account immediately. Refreshing and changing pages keep working. Closing the page ends the session about 5 minutes later, because browsers can't reliably report that someone left. **Done when:** tests cover all of these, and every data table is cleared.
- **8.6 Demo Mode button** (S). **Done when:** it works from the sign-in page on desktop and phones and by keyboard, and shows a "Setting up…" state.
- **8.7 Demo indicators** (S). **Done when:** demo accounts show a DEMO badge, End Demo and Replay Tour, and real accounts see no change.
- **8.8 Video-game character tour** (M). The headband-and-mustache character pops up with a chat bubble and types out his lines while the page dims and a neon ring highlights what he's talking about. About five stops, ending on Home. **Done when:** it can be completed, skipped and replayed at desktop and phone sizes, with keyboard, screen reader and reduced-motion support, and the app works normally afterward.
