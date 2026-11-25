"""Daily Neon snapshot of the production database (run by .github/workflows/backup.yml).

Neon's free plan keeps 6 hours of history and allows one manual snapshot. This job keeps
that one snapshot fresh: it deletes yesterday's snapshot, takes a new one, waits for Neon to
finish, and checks the new one is listed. A failing run makes GitHub email the owner.

It only ever deletes snapshots it made itself (names starting "daily-"). If something else
is using the free plan's only slot, it stops and says so rather than delete it.

Settings come from environment variables, kept as GitHub secrets:
    NEON_API_KEY     a Neon API key scoped to this project
    NEON_PROJECT_ID  the Neon project
    NEON_BRANCH_ID   the production branch to snapshot

Standard library only, so the workflow needs no installs. Nothing it prints includes the
key or anything Neon sends back beyond status codes and snapshot names.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from urllib.parse import quote, urlencode

API = "https://console.neon.tech/api/v2"
PREFIX = "daily-"
TIMEOUT_SECONDS = 30
WAIT_SECONDS = 300  # how long to wait for Neon to finish an operation
POLL_SECONDS = 5
LOCKED_RETRIES = 6  # Neon answers 423 while another operation on the project is running
DONE = "finished"
FAILED = {"failed", "error", "cancelled", "cancelling", "skipped"}
USER_AGENT = "SweatEquity-backup"


class ApiError(Exception):
    def __init__(self, status, step):
        self.status = status
        hint = " (check the NEON_API_KEY secret)" if status in (401, 403) else ""
        super().__init__(f"Neon API answered {status} while trying to {step}{hint}")


def make_api(key, opener=urllib.request.urlopen):
    """A function that calls the Neon API and returns the decoded JSON (or {})."""

    def api(method, path, step, query=None):
        url = API + path + ("?" + urlencode(query) if query else "")
        request = urllib.request.Request(
            url,
            method=method,
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": USER_AGENT},
        )
        try:
            with opener(request, timeout=TIMEOUT_SECONDS) as res:
                body = res.read()
        except urllib.error.HTTPError as err:
            raise ApiError(err.code, step) from None
        return json.loads(body) if body else {}

    return api


def call(api, method, path, step, query=None, sleep=time.sleep):
    """Call the API, waiting and retrying while Neon says the project is busy (423)."""
    for attempt in range(LOCKED_RETRIES + 1):
        try:
            return api(method, path, step, query)
        except ApiError as err:
            if err.status != 423 or attempt == LOCKED_RETRIES:
                raise
            sleep(POLL_SECONDS)


def wait_for(api, project, operations, step, sleep=time.sleep, clock=time.monotonic):
    """Wait until every operation Neon started has finished. Raises if one fails or stalls."""
    deadline = clock() + WAIT_SECONDS
    for op in operations or []:
        status = op.get("status")
        while status != DONE:
            if status in FAILED:
                raise RuntimeError(f"Neon couldn't {step}: an operation ended as '{status}'")
            if clock() > deadline:
                raise RuntimeError(f"Neon didn't finish trying to {step} within {WAIT_SECONDS} seconds")
            sleep(POLL_SECONDS)
            res = call(api, "GET", f"/projects/{project}/operations/{quote(op['id'])}", step, sleep=sleep)
            status = res.get("operation", {}).get("status")


def run(api, project, branch, now=None, out=print, sleep=time.sleep, clock=time.monotonic):
    """Replace the daily snapshot with a fresh one. Returns True on success."""
    now = now or datetime.now(UTC)
    name = PREFIX + now.strftime("%Y-%m-%dT%H%MZ")
    try:
        listed = call(api, "GET", f"/projects/{project}/snapshots", "list snapshots", sleep=sleep)
        snapshots = listed.get("snapshots", [])
        ours = [s for s in snapshots if s.get("name", "").startswith(PREFIX)]
        others = [s for s in snapshots if not s.get("name", "").startswith(PREFIX)]
        if others:
            out(
                f"FAIL  {len(others)} snapshot(s) not made by this job are using the free plan's only slot. "
                "Delete or rename them in Neon (Backup & restore), then rerun. Nothing was changed."
            )
            return False

        for old in ours:
            res = call(
                api,
                "DELETE",
                f"/projects/{project}/snapshots/{quote(old['id'])}",
                "delete the old snapshot",
                sleep=sleep,
            )
            wait_for(api, project, res.get("operations"), "delete the old snapshot", sleep, clock)
            out(f"ok    deleted {old.get('name')}")

        res = call(
            api,
            "POST",
            f"/projects/{project}/branches/{branch}/snapshot",
            "take a snapshot",
            query={"name": name},
            sleep=sleep,
        )
        wait_for(api, project, res.get("operations"), "take a snapshot", sleep, clock)

        listed = call(api, "GET", f"/projects/{project}/snapshots", "list snapshots", sleep=sleep)
        if not any(s.get("name") == name for s in listed.get("snapshots", [])):
            out(f"FAIL  {name} was taken but isn't listed")
            return False
    except (ApiError, RuntimeError) as err:
        out(f"FAIL  {err}")
        return False
    except OSError as err:  # can't connect, DNS failure, timeout
        out(f"FAIL  couldn't reach Neon ({type(err).__name__})")
        return False

    out(f"ok    took {name}")
    return True


def main(environ=os.environ):
    key, project, branch = (environ.get(n, "").strip() for n in ("NEON_API_KEY", "NEON_PROJECT_ID", "NEON_BRANCH_ID"))
    if not (key and project and branch):
        print("Set NEON_API_KEY, NEON_PROJECT_ID and NEON_BRANCH_ID (GitHub secrets).", file=sys.stderr)
        return 2
    return 0 if run(make_api(key), quote(project), quote(branch)) else 1


if __name__ == "__main__":
    sys.exit(main())
