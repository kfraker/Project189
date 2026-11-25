# Backups and restoring the database

How the production database is backed up, what can and can't be recovered, and the steps to restore it. The reasoning is in the [decision log](decisions.md) (2026-11-09).

## What's covered

The database is Postgres on Neon's free plan. Two things protect it:

| | How far back | How it's made |
|---|---|---|
| **Instant restore** | Any moment in the last **6 hours** | Neon keeps it automatically |
| **Daily snapshot** | One copy, **up to a day old** | The [Daily backup](../.github/workflows/backup.yml) workflow replaces it every day at 07:41 UTC |

The free plan allows only one manual snapshot, so the job deletes yesterday's before taking today's. It only deletes snapshots whose names start with `daily-`. If you take your own snapshot in Neon, the job stops and emails you rather than delete it.

**Not covered:** a problem that started more than 6 hours ago *and* is still unnoticed when the next snapshot runs. By then the only snapshot already contains the problem. Neon's paid plans keep up to 30 days; this is the gap the free plan leaves.

## If something has gone wrong with the data

1. **Stop the next snapshot from overwriting the good one.** In GitHub, go to Actions > Daily backup > ⋯ > **Disable workflow**. Do this first.
2. Work out roughly when the problem started.
3. If it started **less than 6 hours ago**, use instant restore (below). Otherwise, if it started **before** the time in the snapshot's name, use the snapshot (below). If neither, the data can't be recovered from backups.

> **The production branch is shared.** It holds two databases: `neondb` (Sweat Equity) and `faceless_channels` (the Faceless Channels app). Restores and snapshots cover the whole branch, so restoring onto the production branch rolls **both** back. If only Sweat Equity's data is wrong, restore into a new branch instead and copy just the `neondb` data back, or accept that Faceless Channels loses the same stretch of changes. Backlog #30 moves `faceless_channels` out of this project, which removes the problem.

## Restore to a moment in the last 6 hours

1. In the [Neon console](https://console.neon.tech), open the project and go to **Backup & restore**.
2. Pick the production branch and the time to go back to. Use **Time Travel** to look at the data at that moment before committing to it.
3. Restore. Neon saves the branch as it was just before the restore as a backup branch, so a mistake here can be undone the same way.

## Restore from the daily snapshot

1. In the Neon console, go to **Backup & restore**, find the `daily-…` snapshot and choose **Restore**.
2. To check it first, restore it into a **new branch** and look at the data there. When you're happy, restore it onto the production branch.
3. Neon again keeps the pre-restore branch as a backup.

## After any restore

1. Visit [/health](https://sweatequity.kfraker.dev/health): it should say `ok`.
2. Sign in and check recent workouts and weigh-ins look right.
3. Re-enable the Daily backup workflow, then run it by hand (Run workflow) so the snapshot is fresh.
4. Delete any leftover backup branches in Neon once you're sure.
5. Note what happened and what was lost in the changelog.

The restore keeps the production branch, so the app's connection settings in Vercel don't change.

## Before a release or a risky change

Run Actions > Daily backup > **Run workflow**, and wait for it to pass. That gives a snapshot from just before the change.

## One-time setup

The workflow needs three GitHub secrets (Settings > Secrets and variables > Actions):

- `NEON_API_KEY`: a Neon API key scoped to this project only. Create it in the Neon console under Organization settings > API keys, choosing **project-scoped**. It can manage this project's branches and snapshots but can't delete the project.
- `NEON_PROJECT_ID`: the project ID, from the project's Settings page.
- `NEON_BRANCH_ID`: the production branch's ID (it starts `br-`), from its page under Branches.

To add one without it ever being shown or saved anywhere else, run `gh secret set NEON_API_KEY` and paste it at the prompt.

## Proven restore

Tested on 2026-11-16 (story 5.4), against production, using a one-off script run through the Neon API with a project-scoped key. Each method restored into a throwaway branch, which was deleted straight afterwards. Production was only read, never changed.

| Method | Restored from | Result | Time to a usable copy |
|---|---|---|---|
| Instant restore | Production as it was 5 minutes earlier | Every table matched | 10.7s and 12.7s (two runs) |
| Daily snapshot | `daily-2026-11-16T0504Z`, taken for the test | Every table matched | 12.7s and 10.7s (two runs) |

"Time to a usable copy" runs from asking Neon for the branch to having counted every row in it. That covers creating the branch and its compute, the cold start, and connecting.

Row counts in Sweat Equity's database (`neondb`), production versus restored:

| Table | Rows |
|---|---|
| preferences | 63 |
| weights | 15 |
| settings | 4 |
| workouts | 4 |
| users | 2 |
| workout_day_notes | 2 |
| schema_migrations | 1 |
| **Total** | **91** |

The `faceless_channels` database on the same branch (16 tables, 31 rows) also matched both times. The first run found it by accident: the script counted the first database it found, which was the wrong one. That's how the shared-branch warning above came to light, so the second run counted every database.

The snapshot taken for the test was left in place. The nightly job replaces it, since its name starts with `daily-`.
