"""The visitor's "today": stats count days from the date on the visitor's own clock.

The live server runs in UTC, which for US visitors is already tomorrow from 7–8pm.
Pages send their local date as ?today=YYYY-MM-DD, and the server uses it when it's
within a day of its own date (every time zone falls in that window). Here the
server's date is pinned to a fixed day, so these tests behave the same at any hour
on any machine.
"""

from datetime import date

import pytest

import app as app_module
from tests.conftest import seed_weight

SERVER_TODAY = date(2030, 1, 2)  # 1am UTC on Jan 2 ...
VISITOR_TODAY = "2030-01-01"  # ... is 8pm on Jan 1 in New York


@pytest.fixture(autouse=True)
def _server_date(monkeypatch):
    monkeypatch.setattr(app_module, "_server_today", lambda: SERVER_TODAY)


def _weight_stats(client, query=""):
    return client.get(f"/api/weight/stats{query}").get_json()


def _home_stats(client, query=""):
    return client.get(f"/api/home-stats{query}").get_json()


def _log_workout(client, day, kcal):
    client.post("/api/workout", json={"date": day, "type": "Yoga", "duration_min": 30, "kcal": kcal, "note": ""})


def test_weigh_in_streak_keeps_counting_in_the_evening(client):
    """Regression: logged today and yesterday, but the server's UTC date had already
    moved on, so the Weigh-ins streak showed 0 every evening."""
    seed_weight(client, "2029-12-31", 200.0)
    seed_weight(client, VISITOR_TODAY, 199.0)
    assert _weight_stats(client, f"?today={VISITOR_TODAY}")["streak"] == 2


def test_seven_day_average_ends_on_the_visitors_today(client):
    seed_weight(client, "2029-12-26", 210.0)  # 7th day back for the visitor, 8th for the server
    seed_weight(client, VISITOR_TODAY, 200.0)
    assert _weight_stats(client, f"?today={VISITOR_TODAY}")["avg_7d"] == 205.0


def test_home_weekly_burn_covers_the_visitors_last_seven_days(client):
    _log_workout(client, "2029-12-25", 50)  # 8th day back: outside the week
    _log_workout(client, "2029-12-26", 100)  # 7th day back for the visitor
    _log_workout(client, VISITOR_TODAY, 200)
    assert _home_stats(client, f"?today={VISITOR_TODAY}")["kcal_week"] == 300


def test_without_a_date_the_server_uses_its_own(client):
    seed_weight(client, VISITOR_TODAY, 199.0)
    assert _weight_stats(client)["streak"] == 0  # the server's Jan 2 has no weigh-in


@pytest.mark.parametrize(
    "sent",
    [
        pytest.param("2029-12-30", id="two-days-behind"),
        pytest.param("2030-01-04", id="two-days-ahead"),
        pytest.param("2030-13-01", id="not-a-date"),
        pytest.param("yesterday", id="not-a-date-format"),
    ],
)
def test_an_implausible_date_is_ignored(client, sent):
    seed_weight(client, VISITOR_TODAY, 199.0)
    assert _weight_stats(client, f"?today={sent}")["streak"] == 0


@pytest.mark.parametrize("sent", ["2030-01-01", "2030-01-02", "2030-01-03"])
def test_a_date_within_a_day_of_the_server_is_used(client, sent):
    seed_weight(client, sent, 199.0)
    assert _weight_stats(client, f"?today={sent}")["streak"] == 1
