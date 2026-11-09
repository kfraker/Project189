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

*Filled in by story 5.4: a restore into a throwaway branch, row counts compared with production, and how long it took.*
