"""tools/sandbox/seed_mock_data.py: refuses to run outside the sandbox, and its data looks real."""

import importlib.util
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "sandbox" / "seed_mock_data.py"
spec = importlib.util.spec_from_file_location("seed_mock_data", SCRIPT)
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)

TODAY = date(2026, 10, 31)


@pytest.mark.parametrize("env", [{}, {"APP_ENV": "production"}, {"APP_ENV": "sandbox", "VERCEL": "1"}])
def test_refuses_unless_this_is_the_local_sandbox(env):
    with pytest.raises(SystemExit, match="Refusing"):
        seed.refuse_unless_sandbox(env)


def test_allows_the_local_sandbox():
    seed.refuse_unless_sandbox({"APP_ENV": "sandbox"})


@pytest.mark.parametrize("env", [{"APP_ENV": "production"}, {"APP_ENV": "sandbox", "VERCEL": "1"}])
def test_the_command_stops_before_touching_a_database(env):
    """A dead database address proves it refuses before trying to connect."""
    run_env = {**os.environ, "VERCEL": "", "DATABASE_URL": "postgresql://nobody@invalid.invalid/none", **env}
    done = subprocess.run([sys.executable, str(SCRIPT)], env=run_env, capture_output=True, text=True, timeout=60)
    assert done.returncode != 0
    assert "Refusing to run" in done.stderr


def test_weigh_ins_end_yesterday_with_no_recent_gaps():
    rows = seed.plan_weigh_ins(TODAY)
    dates = {r["date"] for r in rows}
    assert TODAY.isoformat() not in dates
    assert all((TODAY - timedelta(days=i)).isoformat() in dates for i in range(1, seed.STEADY_DAYS + 1))
    assert len(rows) < seed.HISTORY_DAYS  # older history has gaps


def test_weigh_ins_trend_down_with_notes():
    rows = seed.plan_weigh_ins(TODAY)
    assert rows[-1]["weight_lbs"] < rows[0]["weight_lbs"] - 15
    assert any("notes" in r for r in rows)


def test_workouts_are_varied_and_never_on_today():
    workouts, _ = seed.plan_workouts(TODAY)
    assert len({w["type"] for w in workouts}) >= 5
    assert all(w["date"] < TODAY.isoformat() and w["kcal"] > 0 for w in workouts)


def test_mock_data_is_the_same_every_time():
    assert seed.plan_weigh_ins(TODAY) == seed.plan_weigh_ins(TODAY)
    assert seed.plan_workouts(TODAY) == seed.plan_workouts(TODAY)


def test_fills_an_account_through_the_api(client):
    counts = seed.fill_account(client, days=8)
    assert counts["weigh_ins"] == len(client.get("/api/weights?range=all").get_json())
    assert client.get("/api/settings").get_json()["goal_weight"]["value_lbs"] == 189.0
    assert client.get("/api/preferences").get_json()["fight_name"] == "The Comeback Kid"
