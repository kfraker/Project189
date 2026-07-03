"""
Business logic tests — calculations, rules, and cross-endpoint workflows.

These tests verify that the application behaves correctly across multiple
API calls in a single user story, and that the core arithmetic is right.
"""
import pytest
from datetime import date, timedelta
from tests.conftest import seed_weight, seed_setting


TODAY = date.today().isoformat()


def _date_offset(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


# ── Weight conversion accuracy ───────────────────────────────────────────────

class TestWeightConversion:
    """2.2046 lbs per kg, rounded to 1 decimal."""

    def test_220_46_lbs_is_100_kg(self, client):
        seed_weight(client, TODAY, 220.46)
        rows = client.get("/api/weights?range=all").get_json()
        assert rows[0]["weight_kg"] == 100.0

    def test_result_always_one_decimal(self, client):
        for lbs in [100.0, 150.0, 200.5, 333.3, 88.8]:
            seed_weight(client, _date_offset(200), lbs, False)
            rows = client.get("/api/weights?range=all").get_json()
            kg_str = str(rows[-1]["weight_kg"])
            decimal_part = kg_str.split(".")[-1] if "." in kg_str else ""
            assert len(decimal_part) <= 1, f"{lbs} lbs → {rows[-1]['weight_kg']} kg has more than 1 decimal"
            client.delete(f"/api/weight/{_date_offset(200)}")

    def test_setting_conversion_matches_weight_conversion(self, client):
        """Same formula used in both endpoints."""
        lbs = 185.5
        seed_weight(client, TODAY, lbs)
        seed_setting(client, "start", lbs)
        weight_kg  = client.get("/api/weights?range=all").get_json()[0]["weight_kg"]
        setting_kg = client.get("/api/settings").get_json()["start"]["value_kg"]
        assert weight_kg == setting_kg


# ── Date range boundary conditions ───────────────────────────────────────────

class TestDateRangeBoundaries:

    def test_7d_window_anchors_to_most_recent_entry(self, client):
        """7D = most recent entry and 6 days back = 7 days total."""
        anchor   = _date_offset(3)       # most recent entry — sets the anchor
        boundary = _date_offset(3 + 6)   # exactly 6 days before anchor — included
        outside  = _date_offset(3 + 7)   # 7 days before anchor — excluded
        seed_weight(client, anchor,   200.0)
        seed_weight(client, boundary, 201.0)
        seed_weight(client, outside,  202.0)
        rows  = client.get("/api/weights?range=7d").get_json()
        dates = [r["date"] for r in rows]
        assert anchor   in dates
        assert boundary in dates
        assert outside  not in dates

    def test_1y_window_is_364_days_back_from_most_recent(self, client):
        """1Y = 365 days, so boundary is most recent entry − 364."""
        anchor   = _date_offset(5)
        boundary = _date_offset(5 + 364)
        outside  = _date_offset(5 + 365)
        seed_weight(client, anchor,   200.0)
        seed_weight(client, boundary, 201.0)
        seed_weight(client, outside,  202.0)
        rows  = client.get("/api/weights?range=1y").get_json()
        dates = [r["date"] for r in rows]
        assert boundary in dates
        assert outside  not in dates

    def test_leap_year_date_stored_and_retrieved(self, client):
        """Feb 29 on a leap year should round-trip correctly."""
        leap_day = "2024-02-29"
        seed_weight(client, leap_day, 200.0)
        rows = client.get("/api/weights?range=all").get_json()
        assert any(r["date"] == leap_day for r in rows)

    def test_year_boundary_jan_1_stored_correctly(self, client):
        seed_weight(client, "2026-01-01", 200.0)
        seed_weight(client, "2025-12-31", 201.0)
        rows = client.get("/api/weights?range=all").get_json()
        dates = [r["date"] for r in rows]
        assert "2025-12-31" in dates
        assert "2026-01-01" in dates
        assert dates == sorted(dates)


# ── Dashboard / workflow rules ────────────────────────────────────────────────

class TestDashboardWorkflows:

    def test_logging_current_weight_creates_historical_entry(self, client):
        """Every weight log becomes a historical entry (no separate current table)."""
        seed_weight(client, TODAY, 200.0)
        rows = client.get("/api/weights?range=all").get_json()
        assert len(rows) == 1
        assert rows[0]["date"] == TODAY

    def test_editing_historical_weight_does_not_create_duplicate(self, client):
        seed_weight(client, "2026-01-15", 200.0)
        seed_weight(client, "2026-01-15", 195.0, overwrite=True)
        rows = client.get("/api/weights?range=all").get_json()
        assert len(rows) == 1

    def test_editing_historical_weight_updates_chart_data(self, client):
        seed_weight(client, "2026-01-15", 200.0)
        seed_weight(client, "2026-01-15", 195.0, overwrite=True)
        rows = client.get("/api/weights?range=all").get_json()
        assert rows[0]["weight_lbs"] == 195.0

    def test_weight_lost_is_start_minus_current(self, client):
        """Client calculates weight lost; verify the data for it is correct."""
        seed_setting(client, "start", 220.0)
        seed_weight(client, TODAY, 200.0)
        settings = client.get("/api/settings").get_json()
        latest   = client.get("/api/latest-weight").get_json()
        weight_lost = settings["start"]["value_lbs"] - latest["weight_lbs"]
        assert weight_lost == pytest.approx(20.0)

    def test_goal_progress_data_is_accessible(self, client):
        seed_setting(client, "start", 220.0)
        seed_setting(client, "goal",  180.0)
        seed_weight(client, TODAY, 200.0)
        settings = client.get("/api/settings").get_json()
        latest   = client.get("/api/latest-weight").get_json()
        total_to_lose  = settings["start"]["value_lbs"] - settings["goal"]["value_lbs"]
        already_lost   = settings["start"]["value_lbs"] - latest["weight_lbs"]
        progress_pct   = already_lost / total_to_lose * 100
        assert total_to_lose == pytest.approx(40.0)
        assert already_lost  == pytest.approx(20.0)
        assert progress_pct  == pytest.approx(50.0)

    def test_date_ordering_maintained_after_multiple_inserts(self, client):
        dates = [_date_offset(i) for i in [10, 2, 7, 1, 4]]
        for i, d in enumerate(dates):
            seed_weight(client, d, 200.0 + i)
        rows = client.get("/api/weights?range=all").get_json()
        retrieved_dates = [r["date"] for r in rows]
        assert retrieved_dates == sorted(retrieved_dates)

    def test_latest_weight_updates_after_new_entry(self, client):
        seed_weight(client, _date_offset(1), 202.0)
        assert client.get("/api/latest-weight").get_json()["weight_lbs"] == 202.0
        seed_weight(client, TODAY, 200.0)
        assert client.get("/api/latest-weight").get_json()["weight_lbs"] == 200.0

    def test_delete_updates_latest_weight(self, client):
        seed_weight(client, _date_offset(1), 202.0)
        seed_weight(client, TODAY, 200.0)
        client.delete(f"/api/weight/{TODAY}")
        assert client.get("/api/latest-weight").get_json()["weight_lbs"] == 202.0

    def test_oldest_date_updates_when_oldest_deleted(self, client):
        seed_weight(client, "2026-01-01", 205.0)
        seed_weight(client, "2026-02-01", 200.0)
        client.delete("/api/weight/2026-01-01")
        latest = client.get("/api/latest-weight").get_json()
        assert latest["oldest_date"] == "2026-02-01"


# ── Custom range capping ──────────────────────────────────────────────────────

class TestCustomRangeCapping:

    def test_days_exactly_1095_accepted(self, client):
        r = client.get("/api/weights?range=custom&days=1095")
        assert r.status_code == 200

    def test_days_1096_capped_to_1095(self, client):
        """days=1096 → treated as 1095. Check it doesn't 500."""
        r = client.get("/api/weights?range=custom&days=1096")
        assert r.status_code == 200

    def test_days_0_treated_as_30_via_or_fallback(self, client):
        """0 or 30 == 30 in Python; default kicks in. Anchor = most recent entry."""
        anchor   = _date_offset(2)
        boundary = _date_offset(2 + 29)
        outside  = _date_offset(2 + 30)
        seed_weight(client, anchor,   200.0)
        seed_weight(client, boundary, 201.0)
        seed_weight(client, outside,  202.0)
        rows  = client.get("/api/weights?range=custom&days=0").get_json()
        dates = [r["date"] for r in rows]
        assert anchor   in dates
        assert boundary in dates
        assert outside  not in dates
