"""The daily snapshot job (tools/backup/snapshot.py) keeps exactly one fresh snapshot, only
ever deletes its own, and fails loudly, without leaking the key, when Neon says no."""

import importlib.util
import io
import urllib.error
from datetime import UTC, datetime
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "snapshot", Path(__file__).resolve().parents[1] / "tools" / "backup" / "snapshot.py"
)
snapshot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(snapshot)

NOW = datetime(2026, 11, 9, 7, 41, tzinfo=UTC)
NEW_NAME = "daily-2026-11-09T0741Z"
KEY = "napi_super_secret_test_key"


class FakeNeon:
    """Just enough of Neon's snapshot API, with operations that take a couple of polls."""

    def __init__(self, snapshots=(), polls_to_finish=2, fail_on=None, op_ends="finished"):
        self.snapshots = [dict(s) for s in snapshots]
        self.polls_to_finish = polls_to_finish
        self.fail_on = fail_on or {}  # (method, step) -> HTTP status
        self.op_ends = op_ends
        self.ops = {}
        self.calls = []

    def _op(self):
        op_id = f"op-{len(self.ops) + 1}"
        self.ops[op_id] = self.polls_to_finish
        return {"id": op_id, "status": "running"}

    def __call__(self, method, path, step, query=None):
        self.calls.append((method, path, query))
        status = self.fail_on.get((method, step))
        if status:
            raise snapshot.ApiError(status, step)
        if method == "GET" and path.endswith("/snapshots"):
            return {"snapshots": [dict(s) for s in self.snapshots]}
        if method == "GET" and "/operations/" in path:
            op_id = path.rsplit("/", 1)[1]
            self.ops[op_id] -= 1
            return {"operation": {"id": op_id, "status": self.op_ends if self.ops[op_id] <= 0 else "running"}}
        if method == "DELETE":
            snap_id = path.rsplit("/", 1)[1]
            self.snapshots = [s for s in self.snapshots if s["id"] != snap_id]
            return {"operations": [self._op()]}
        if method == "POST" and path.endswith("/snapshot"):
            if len(self.snapshots) >= 1:  # the free plan's limit
                raise snapshot.ApiError(422, step)
            self.snapshots.append({"id": f"snap-{len(self.calls)}", "name": query["name"]})
            return {"snapshot": self.snapshots[-1], "operations": [self._op()]}
        raise AssertionError(f"unexpected call {method} {path}")


@pytest.fixture()
def lines():
    return []


def go(neon, lines, **kwargs):
    kwargs.setdefault("clock", lambda: 0)
    return snapshot.run(neon, "proj-1", "br-main", now=NOW, out=lines.append, sleep=lambda s: None, **kwargs)


def test_first_run_takes_a_snapshot(lines):
    neon = FakeNeon()
    assert go(neon, lines)
    assert [s["name"] for s in neon.snapshots] == [NEW_NAME]
    assert lines[-1] == f"ok    took {NEW_NAME}"


def test_replaces_yesterdays_snapshot_and_waits_for_neon(lines):
    neon = FakeNeon(snapshots=[{"id": "snap-old", "name": "daily-2026-11-08T0741Z"}])
    assert go(neon, lines)
    assert [s["name"] for s in neon.snapshots] == [NEW_NAME]
    methods = [c[0] for c in neon.calls]
    # delete, then poll until done, before taking the new one
    assert methods.index("DELETE") < methods.index("POST")
    assert all(left <= 0 for left in neon.ops.values()), "every operation was waited on"
    assert "ok    deleted daily-2026-11-08T0741Z" in lines


def test_never_deletes_a_snapshot_it_didnt_make(lines):
    neon = FakeNeon(snapshots=[{"id": "snap-mine", "name": "before-big-change"}])
    assert not go(neon, lines)
    assert neon.snapshots == [{"id": "snap-mine", "name": "before-big-change"}]
    assert not [c for c in neon.calls if c[0] in ("DELETE", "POST")], "nothing was changed"
    assert "not made by this job" in lines[-1]


def test_neon_operation_failing_fails_the_run(lines):
    neon = FakeNeon(op_ends="failed")
    assert not go(neon, lines)
    assert lines[-1] == "FAIL  Neon couldn't take a snapshot: an operation ended as 'failed'"


def test_operation_that_never_finishes_times_out(lines):
    neon = FakeNeon(polls_to_finish=10**6)
    ticks = iter(range(0, 10**6, 60))
    assert not go(neon, lines, clock=lambda: next(ticks))
    assert "didn't finish trying to take a snapshot" in lines[-1]


def test_snapshot_missing_afterwards_fails(lines):
    neon = FakeNeon()
    real = neon.__call__

    def forgetful(method, path, step, query=None):
        res = real(method, path, step, query)
        if method == "GET" and path.endswith("/snapshots") and any(c[0] == "POST" for c in neon.calls):
            return {"snapshots": []}
        return res

    assert not go(forgetful, lines)
    assert lines[-1] == f"FAIL  {NEW_NAME} was taken but isn't listed"


def test_busy_project_is_retried(lines):
    neon = FakeNeon()
    real = neon.__call__
    busy = {"left": 2}

    def sometimes_locked(method, path, step, query=None):
        if method == "POST" and busy["left"]:
            busy["left"] -= 1
            raise snapshot.ApiError(423, step)
        return real(method, path, step, query)

    assert go(sometimes_locked, lines)
    assert [s["name"] for s in neon.snapshots] == [NEW_NAME]


@pytest.mark.parametrize(
    ("fail_on", "expected"),
    [
        ({("GET", "list snapshots"): 401}, "401 while trying to list snapshots (check the NEON_API_KEY secret)"),
        ({("POST", "take a snapshot"): 500}, "500 while trying to take a snapshot"),
    ],
)
def test_api_errors_fail_with_a_plain_message(lines, fail_on, expected):
    assert not go(FakeNeon(fail_on=fail_on), lines)
    assert lines[-1] == f"FAIL  Neon API answered {expected}"


def test_unreachable_neon_fails(lines):
    def offline(*args, **kwargs):
        raise urllib.error.URLError("no network")

    assert not go(offline, lines)
    assert lines[-1] == "FAIL  couldn't reach Neon (URLError)"


def test_api_sends_the_key_only_in_the_header_and_never_echoes_it():
    seen = {}

    def opener(request, timeout):
        seen["auth"] = request.get_header("Authorization")
        seen["url"] = request.full_url
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, io.BytesIO(f"bad key {KEY}".encode()))

    api = snapshot.make_api(KEY, opener=opener)
    with pytest.raises(snapshot.ApiError) as err:
        api("POST", "/projects/p/branches/b/snapshot", "take a snapshot", {"name": NEW_NAME})
    assert seen["auth"] == f"Bearer {KEY}"
    assert seen["url"] == f"https://console.neon.tech/api/v2/projects/p/branches/b/snapshot?name={NEW_NAME}"
    assert KEY not in str(err.value)


def test_command_line_needs_all_three_settings(capsys):
    assert snapshot.main({"NEON_API_KEY": KEY, "NEON_PROJECT_ID": "p"}) == 2
    assert KEY not in capsys.readouterr().err
